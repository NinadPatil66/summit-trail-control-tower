from summit_gen.master import generate_master, read_master

FILES = ["dc", "carrier", "supplier", "product", "customer", "kit_bom", "sku_crosswalk"]


def test_writes_all_seven_files_per_extract(small_cfg):
    folders = generate_master(small_cfg)
    assert len(folders) == 9                      # one per quarter over two years
    for folder in folders:
        for name in FILES:
            assert (folder / f"{name}.csv").exists(), f"missing {name}.csv in {folder.name}"


def test_row_counts_and_unique_keys(small_cfg):
    generate_master(small_cfg)
    ent = small_cfg["entities"]
    product, supplier = read_master(small_cfg, "product"), read_master(small_cfg, "supplier")
    assert len(read_master(small_cfg, "dc")) == 6
    assert len(read_master(small_cfg, "carrier")) == 5
    assert len(supplier) == ent["suppliers"] and supplier["supplier_code"].is_unique
    assert len(product) == ent["skus"] and product["sku_code"].is_unique
    assert len(read_master(small_cfg, "customer")) <= ent["customers"]


def test_every_supplier_has_a_sku_and_kits_have_no_self_reference(small_cfg):
    generate_master(small_cfg)
    product, kits = read_master(small_cfg, "product"), read_master(small_cfg, "kit_bom")
    assert set(read_master(small_cfg, "supplier")["supplier_id"]) <= set(product["primary_supplier_id"])
    assert (kits["kit_sku_id"] != kits["component_sku_id"]).all()


def test_costs_change_between_extracts(small_cfg):
    generate_master(small_cfg)
    history = read_master(small_cfg, "product", all_extracts=True)
    versions = history.groupby("sku_code")["unit_cost"].nunique()
    assert (versions > 1).any(), "no SKU ever changed cost, so snapshots would have nothing to record"