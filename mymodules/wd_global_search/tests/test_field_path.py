from unittest import TestCase

from ..services.field_path import (
    FieldPathError,
    operator_domain,
    validate_field_path,
    wrap_path_domain,
)


class FakeField:
    def __init__(self, field_type, comodel_name=None, store=True):
        self.type = field_type
        self.comodel_name = comodel_name
        self.store = store


class FakeEnvironment(dict):
    pass


class FakeModel:
    def __init__(self, name, fields, env=None):
        self._name = name
        self._fields = fields
        self.env = env


def field_path_models():
    env = FakeEnvironment()
    env["sale.order"] = FakeModel(
        "sale.order",
        {
            "partner_id": FakeField("many2one", "res.partner"),
            "category_ids": FakeField("many2many", "res.partner.category"),
            "order_line": FakeField("one2many", "sale.order.line"),
        },
        env,
    )
    env["res.partner"] = FakeModel(
        "res.partner",
        {
            "city": FakeField("char"),
            "country_id": FakeField("many2one", "res.country"),
            "parent_id": FakeField("many2one", "res.partner"),
        },
        env,
    )
    env["res.country"] = FakeModel(
        "res.country",
        {
            "name": FakeField("char"),
            "region_id": FakeField("many2one", "res.country.region"),
        },
        env,
    )
    env["res.country.region"] = FakeModel(
        "res.country.region",
        {
            "name": FakeField("char"),
            "zone_id": FakeField("many2one", "res.country.zone"),
        },
        env,
    )
    env["res.country.zone"] = FakeModel(
        "res.country.zone", {"name": FakeField("char")}, env
    )
    env["res.partner.category"] = FakeModel(
        "res.partner.category",
        {
            "name": FakeField("char"),
            "parent_id": FakeField("many2one", "res.partner.category"),
        },
        env,
    )
    env["sale.order.line"] = FakeModel(
        "sale.order.line", {"product_id": FakeField("many2one", "product.product")}, env
    )
    env["product.product"] = FakeModel(
        "product.product",
        {
            "name": FakeField("char"),
            "category_id": FakeField("many2one", "product.category"),
        },
        env,
    )
    env["product.category"] = FakeModel(
        "product.category",
        {"name": FakeField("char"), "parent_id": FakeField("many2one", "product.category")},
        env,
    )
    return env


class TestFieldPath(TestCase):
    def setUp(self):
        self.env = field_path_models()
        self.root = self.env["sale.order"]

    def test_many2one_paths_allow_one_to_three_hops(self):
        for path in (
            "partner_id.city",
            "partner_id.country_id.name",
            "partner_id.country_id.region_id.name",
        ):
            with self.subTest(path=path):
                resolved = validate_field_path(self.root, path, "contains", "gin_trgm")
                self.assertEqual(resolved.relation_depth, path.count("."))

    def test_many2one_four_hops_are_rejected(self):
        with self.assertRaises(FieldPathError):
            validate_field_path(
                self.root,
                "partner_id.country_id.region_id.zone_id.name",
                "contains",
                "gin_trgm",
            )

    def test_many2many_and_one2many_paths_have_bounded_shapes(self):
        self.assertEqual(
            validate_field_path(
                self.root, "category_ids.parent_id.name", "contains", "gin_trgm"
            ).relation_depth,
            2,
        )
        self.assertEqual(
            validate_field_path(
                self.root,
                "order_line.product_id.category_id.name",
                "contains",
                "gin_trgm",
            ).relation_depth,
            3,
        )
        with self.assertRaises(FieldPathError):
            validate_field_path(
                self.root,
                "category_ids.parent_id.parent_id.name",
                "contains",
                "gin_trgm",
            )
        with self.assertRaises(FieldPathError):
            validate_field_path(
                self.root,
                "order_line.product_id.category_id.parent_id.name",
                "contains",
                "gin_trgm",
            )

    def test_invalid_syntax_and_terminal_relation_are_rejected(self):
        for path in (
            "partner_id[0].city",
            "partner_id..city",
            "partner_id.city|upper",
            "partner_id.city()",
            "partner_id",
            "x" * 101,
        ):
            with self.subTest(path=path):
                with self.assertRaises(FieldPathError):
                    validate_field_path(self.root, path)

    def test_repeated_relation_edge_and_resource_depth_are_rejected(self):
        with self.assertRaises(FieldPathError):
            validate_field_path(
                self.root, "partner_id.parent_id.parent_id.name"
            )
        with self.assertRaises(FieldPathError):
            validate_field_path(
                self.root, "partner_id.country_id.name", max_relation_depth=1
            )

    def test_operator_and_collection_configuration_are_type_checked(self):
        with self.assertRaises(FieldPathError):
            validate_field_path(
                self.root,
                "partner_id.city",
                operator_set="contains",
                index_strategy="btree",
            )
        with self.assertRaises(FieldPathError):
            validate_field_path(
                self.root,
                "partner_id.country_id.name",
                collection_match="all",
            )
        resolved = validate_field_path(
            self.root,
            "category_ids.name",
            "contains",
            "gist_trgm",
            collection_match="all",
        )
        self.assertTrue(resolved.collection_match_applicable)

    def test_relation_domain_uses_nested_any_and_published_operator(self):
        resolved = validate_field_path(
            self.root, "partner_id.country_id.name", "prefix", "pattern_ops"
        )
        operator, value = operator_domain("prefix", "Acme")
        domain = wrap_path_domain(
            resolved, [(resolved.segments[-1], operator, value)]
        )

        self.assertEqual(
            domain,
            [
                (
                    "partner_id",
                    "any",
                    [
                        (
                            "country_id",
                            "any",
                            [("name", "ilike", "Acme%")],
                        )
                    ],
                )
            ],
        )
