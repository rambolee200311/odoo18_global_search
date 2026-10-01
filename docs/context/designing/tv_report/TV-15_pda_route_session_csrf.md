# TV-15：独立 PDA 路由、Session 与 CSRF

## 验证结论

**可行。使用 Odoo Controller 的 `auth='user'`、标准 Session 和 OWL 资源包即可。**

## 路由建议

页面路由：

```python
@http.route('/blind_count/pda', type='http', auth='user', methods=['GET'])
def pda_home(self):
    request.env['blind.count'].check_access_rights('read')
    return request.render('blind_count.pda_page')
```

业务 RPC：

```python
@http.route(
    '/blind_count/pda/scan',
    type='json',
    auth='user',
    methods=['POST'],
)
def scan(self, blind_count_id, payload):
    count = request.env['blind.count'].browse(blind_count_id)
    count.check_access_rights('write')
    count.check_access_rule('write')
    return count.action_scan(payload)
```

`auth='user'` 负责登录态，但不等于业务权限。模型 ACL、记录规则和业务角色检查仍然必须执行。

## CSRF 与资源

- 页面 GET 路由应保持默认 CSRF 行为；
- 修改业务的 POST/JSON 路由不能关闭 CSRF；
- 只有明确的外部设备接口才考虑 `csrf=False`，且必须使用独立认证；
- OWL JS/CSS 应通过模块 assets bundle 加载；
- PDA Session 复用 Odoo 标准 Session，不在前端保存权限凭据。

## 风险与 SRS 影响

- 自定义路由不能绕过模型权限；
- 不能使用 `sudo()` 作为默认权限方案；
- 独立路由必须有认证过期处理；
- E2E 应验证未登录、无权限和越权记录访问。

SRS 无需改变；TDD 应冻结路由、认证、ACL、CSRF 和资源包契约。

