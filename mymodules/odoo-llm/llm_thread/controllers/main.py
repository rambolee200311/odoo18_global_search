import json
import logging

from odoo import _, api, http
from odoo.exceptions import MissingError
from odoo.http import Response, request
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)


class LLMThreadController(http.Controller):
    @http.route(
        "/llm/thread/<int:thread_id>/update",
        type="json",
        auth="user",
        methods=["POST"],
        csrf=True,
    )
    def llm_thread_update(self, thread_id, **kwargs):
        try:
            thread = request.env["llm.thread"].browse(thread_id)
            if not thread.exists():
                raise MissingError(_("LLM Thread not found."))
            thread.write(kwargs)
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _safe_yield(data_to_yield):
        """Yield an SSE event without making client connectivity control generation."""
        try:
            yield data_to_yield
            return True
        except GeneratorExit:
            # A WSGI server closes the response generator when the browser goes
            # away.  Treat that as a disconnected listener, not as a request to
            # cancel the native assistant/tool loop.
            return False
        except BrokenPipeError:
            return False
        except Exception:
            return False

    @classmethod
    def _llm_thread_generate(cls, dbname, env, thread_id, user_message_body, **kwargs):
        """Generate LLM responses with streaming and safe yielding."""
        with Registry(dbname).cursor() as cr:
            env = api.Environment(cr, env.uid, env.context)
            llm_thread = env["llm.thread"].browse(int(thread_id))
            if not llm_thread.exists():
                yield from cls._safe_yield(
                    f"data: {json.dumps({'type': 'error', 'error': 'LLM Thread not found.'})}\n\n".encode(),
                )
                return

            client_connected = True
            try:
                responses = iter(llm_thread.generate(user_message_body, **kwargs))
                for response in responses:
                    if not client_connected:
                        # Continue consuming the native generator so tool calls
                        # and the follow-up Provider request can finish.  There
                        # is simply no SSE client left to receive these events.
                        continue
                    json_data = json.dumps(response, default=str)
                    try:
                        success = yield from cls._safe_yield(
                            f"data: {json_data}\n\n".encode(),
                        )
                    except GeneratorExit:
                        # ``generator.close()`` is propagated by ``yield from``
                        # even when the delegated SSE generator handles it.
                        # Drain the native assistant generator before returning;
                        # yielding again here would violate close() semantics.
                        client_connected = False
                        _logger.info(
                            "SSE client disconnected during generation for thread %s; "
                            "draining assistant/tool processing",
                            thread_id,
                        )
                        for _response in responses:
                            pass
                        return
                    if not success:
                        client_connected = False
                        _logger.info(
                            "SSE client disconnected during generation for thread %s; "
                            "continuing assistant/tool processing",
                            thread_id,
                        )

            except Exception as e:
                _logger.exception(
                    f"Error in llm_thread_generate for thread {thread_id}: {e}",
                )
                # Lock will be automatically released by context manager

                if client_connected:
                    success = yield from cls._safe_yield(
                        f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n".encode(),
                    )
                    if not success:
                        client_connected = False

            finally:
                if client_connected:
                    yield from cls._safe_yield(
                        f"data: {json.dumps({'type': 'done'})}\n\n".encode(),
                    )

    @http.route("/llm/thread/generate", type="http", auth="user", csrf=True)
    def llm_thread_generate(
        self,
        thread_id,
        message=None,
        attachment_ids=None,
        **kwargs,
    ):
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
        parsed_attachment_ids = []
        if attachment_ids:
            parsed_attachment_ids = [
                int(x) for x in attachment_ids.split(",") if x.strip().isdigit()
            ]
        return Response(
            self._llm_thread_generate(
                request.cr.dbname,
                request.env,
                thread_id,
                message,
                attachment_ids=parsed_attachment_ids,
                **kwargs,
            ),
            direct_passthrough=True,
            headers=headers,
        )
