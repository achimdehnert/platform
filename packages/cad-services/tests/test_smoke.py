def test_import_package():
    import cad_services

    assert hasattr(cad_services, "__version__")
