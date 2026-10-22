import json
attachments=env['ir.attachment'].search([('name','like','TV-SPAWN-RECOVERY-%')])
requests=env['office.document.request'].search([('source_attachment_id','in',attachments.ids)]) if attachments else env['office.document.request'].browse([])
evidence={'matched_attachment_count':len(attachments),'matched_request_count':len(requests),'attachments':[{'id':a.id,'name':a.name,'res_model':a.res_model,'res_id':a.res_id} for a in attachments],'requests':[{'id':r.id,'uuid':r.request_uuid,'state':r.state,'error_code':r.error_code,'failed_stage':r.failed_stage,'output_attachment_id':r.output_attachment_id.id or False} for r in requests]}
if len(attachments)==1 and len(requests)<=1 and attachments[0].name.startswith('TV-SPAWN-RECOVERY-'):
    for req in requests:
        if req.output_attachment_id:
            req.output_attachment_id.unlink()
        req.unlink()
    attachments.unlink()
    env.cr.commit()
    env.invalidate_all()
    evidence['cleanup_committed']=True
    evidence['remaining_marked_attachments']=env['ir.attachment'].search_count([('name','like','TV-SPAWN-RECOVERY-%')])
else:
    evidence['cleanup_committed']=False
    evidence['reason']='Expected exactly one uniquely marked attachment and at most one linked request; no deletion performed.'
print(json.dumps(evidence,ensure_ascii=False))
