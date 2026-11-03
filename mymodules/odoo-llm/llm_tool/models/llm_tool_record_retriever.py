import json
import logging
from typing import Any, Union

from odoo import _, api, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class LLMToolRecordRetriever(models.Model):
    _inherit = "llm.tool"

    @api.model
    def _get_available_implementations(self):
        implementations = super()._get_available_implementations()
        return implementations + [("odoo_record_retriever", "Odoo Record Retriever")]

    def odoo_record_retriever_execute(
        self,
        model: str,
        domain: list[list[Union[str, int, bool, float, None]]] = [],  # noqa: B006
        fields: list[str] = [],  # noqa: B006
        limit: int = 100,
        offset: int = 0,
        order: str = "",
        include_pagination: bool = False,
    ) -> Union[list[dict[str, Any]], dict[str, Any]]:
        """
        Execute the Odoo Record Retriever tool

        Parameters:
            model: The Odoo model to retrieve records from
            domain: Domain to filter records (list of lists/tuples like ['field', 'op', 'value'])
            fields: List of field names to retrieve
            limit: Maximum number of records to retrieve
            offset: Number of matching records to skip before returning this page
            order: Optional Odoo ORM order expression; record ID is appended as a stable tie-breaker
            include_pagination: Return count, offset, limit, and has_more alongside the rows
        """
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValidationError(_("limit must be an integer from 1 to 500."))
        if type(offset) is not int or offset < 0:
            raise ValidationError(_("offset must be a non-negative integer."))
        if order is None:
            order = ""
        if not isinstance(order, str) or len(order) > 512:
            raise ValidationError(_("order must be a short Odoo ORM order expression."))
        if type(include_pagination) is not bool:
            raise ValidationError(_("include_pagination must be boolean."))
        stable_order = order.strip()
        if stable_order and not any(
            part.strip().split()[0].split(".")[-1] == "id"
            for part in stable_order.split(",")
            if part.strip()
        ):
            stable_order = f"{stable_order}, id"
        _logger.info(
            "Executing Odoo Record Retriever with model=%s, domain=%s, fields=%s, limit=%s, offset=%s, order=%s",
            model,
            domain,
            fields,
            limit,
            offset,
            stable_order or None,
        )
        model_obj = self.env[model]

        # Using search_read for efficiency
        if fields:
            result = model_obj.search_read(
                domain=domain,
                fields=fields,
                limit=limit,
                offset=offset,
                order=stable_order or None,
            )
        else:
            records = model_obj.search(
                domain=domain,
                limit=limit,
                offset=offset,
                order=stable_order or None,
            )
            result = records.read()

        # Convert to serializable format
        serializable = json.loads(json.dumps(result, default=str))
        if not include_pagination:
            return serializable
        total_count = model_obj.search_count(domain)
        return {
            "records": serializable,
            "count": total_count,
            "offset": offset,
            "limit": limit,
            "has_more": offset + len(serializable) < total_count,
        }
