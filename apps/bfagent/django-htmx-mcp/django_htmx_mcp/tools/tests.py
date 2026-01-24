"""
Test Generation Tools.

Tools zum Generieren von Django Tests.
"""

from typing import Literal

from django_htmx_mcp.server import mcp, logger
from django_htmx_mcp.templating import snake_case, pluralize


@mcp.tool()
def generate_model_tests(
    model: str,
    app_name: str,
    fields: list[dict] | None = None,
    with_factory: bool = True,
    test_str: bool = True,
    test_absolute_url: bool = True,
    test_constraints: bool = True,
) -> str:
    """
    Generiert Model Tests mit pytest-django.
    
    Args:
        model: Model Name
        app_name: Django App Name
        fields: Field-Definitionen für Factory (optional)
        with_factory: factory_boy Factory generieren
        test_str: __str__ Methode testen
        test_absolute_url: get_absolute_url testen
        test_constraints: Unique Constraints testen
        
    Returns:
        Python Code für Tests
    """
    logger.info(f"Generating model tests for {model}")
    
    model_snake = snake_case(model)
    
    imports = [
        "import pytest",
        f"from {app_name}.models import {model}",
    ]
    
    if with_factory:
        imports.append("import factory")
    
    lines = []
    lines.append("\n".join(sorted(set(imports))))
    lines.extend(["", ""])
    
    # Factory
    if with_factory:
        lines.append(f"class {model}Factory(factory.django.DjangoModelFactory):")
        lines.append(f'    """Factory for {model} model."""')
        lines.append("")
        lines.append("    class Meta:")
        lines.append(f"        model = {model}")
        lines.append("")
        
        if fields:
            for f in fields:
                name = f.get("name")
                ftype = f.get("type", "CharField")
                
                if ftype == "CharField":
                    lines.append(f'    {name} = factory.Faker("word")')
                elif ftype == "TextField":
                    lines.append(f'    {name} = factory.Faker("text")')
                elif ftype == "EmailField":
                    lines.append(f'    {name} = factory.Faker("email")')
                elif ftype == "IntegerField":
                    lines.append(f'    {name} = factory.Faker("random_int")')
                elif ftype == "BooleanField":
                    lines.append(f'    {name} = factory.Faker("boolean")')
                elif ftype == "DateField":
                    lines.append(f'    {name} = factory.Faker("date_object")')
                elif ftype == "DateTimeField":
                    lines.append(f'    {name} = factory.Faker("date_time")')
                elif ftype == "ForeignKey":
                    related = f.get("to", "User")
                    lines.append(f'    {name} = factory.SubFactory("{related}Factory")')
                else:
                    lines.append(f'    {name} = factory.Faker("word")')
        else:
            lines.append('    name = factory.Faker("word")')
        
        lines.extend(["", ""])
    
    # Pytest marker
    lines.append("@pytest.mark.django_db")
    lines.append(f"class Test{model}Model:")
    lines.append(f'    """Tests for {model} model."""')
    lines.append("")
    
    # Test creation
    lines.append("    def test_create(self):")
    lines.append(f'        """Test {model} can be created."""')
    if with_factory:
        lines.append(f"        {model_snake} = {model}Factory()")
    else:
        lines.append(f"        {model_snake} = {model}.objects.create(name='Test')")
    lines.append(f"        assert {model_snake}.pk is not None")
    lines.append("")
    
    # Test __str__
    if test_str:
        lines.append("    def test_str(self):")
        lines.append(f'        """Test {model}.__str__() returns expected value."""')
        if with_factory:
            lines.append(f"        {model_snake} = {model}Factory()")
        else:
            lines.append(f"        {model_snake} = {model}.objects.create(name='Test')")
        lines.append(f"        assert str({model_snake})")
        lines.append(f"        assert isinstance(str({model_snake}), str)")
        lines.append("")
    
    # Test get_absolute_url
    if test_absolute_url:
        lines.append("    def test_get_absolute_url(self):")
        lines.append(f'        """Test {model}.get_absolute_url() returns valid URL."""')
        if with_factory:
            lines.append(f"        {model_snake} = {model}Factory()")
        else:
            lines.append(f"        {model_snake} = {model}.objects.create(name='Test')")
        lines.append(f"        url = {model_snake}.get_absolute_url()")
        lines.append(f"        assert url")
        lines.append(f'        assert f"/{model_snake}.pk" in url or str({model_snake}.pk) in url')
        lines.append("")
    
    # Test constraints
    if test_constraints:
        lines.append("    def test_ordering(self):")
        lines.append(f'        """Test {model} default ordering."""')
        if with_factory:
            lines.append(f"        {model}Factory.create_batch(3)")
        else:
            lines.append(f"        for i in range(3):")
            lines.append(f"            {model}.objects.create(name=f'Test {{i}}')")
        lines.append(f"        {model_plural} = list({model}.objects.all())")
        lines.append(f"        assert len({model_plural}) == 3")
    
    return "\n".join(lines)


@mcp.tool()
def generate_view_tests(
    model: str,
    app_name: str,
    view_type: Literal["list", "detail", "create", "update", "delete"],
    with_htmx: bool = True,
    with_permissions: bool = False,
) -> str:
    """
    Generiert View Tests mit pytest-django.
    
    Args:
        model: Model Name
        app_name: Django App Name
        view_type: Typ der View
        with_htmx: HTMX-spezifische Tests
        with_permissions: Permission Tests
        
    Returns:
        Python Code für View Tests
    """
    logger.info(f"Generating view tests for {model} {view_type}")
    
    model_snake = snake_case(model)
    model_plural = pluralize(model_snake)
    
    imports = [
        "import pytest",
        "from django.urls import reverse",
        f"from {app_name}.models import {model}",
    ]
    
    lines = []
    lines.append("\n".join(sorted(set(imports))))
    lines.extend(["", ""])
    
    # Fixtures
    lines.append("@pytest.fixture")
    lines.append(f"def {model_snake}(db):")
    lines.append(f'    """Create a {model} instance."""')
    lines.append(f"    return {model}.objects.create(name='Test {model}')")
    lines.append("")
    lines.append("")
    
    if with_permissions:
        lines.append("@pytest.fixture")
        lines.append("def authenticated_client(client, django_user_model):")
        lines.append('    """Create an authenticated client."""')
        lines.append("    user = django_user_model.objects.create_user(")
        lines.append("        username='testuser', password='testpass'")
        lines.append("    )")
        lines.append("    client.login(username='testuser', password='testpass')")
        lines.append("    return client")
        lines.append("")
        lines.append("")
    
    # Test class
    lines.append("@pytest.mark.django_db")
    lines.append(f"class Test{model}{view_type.title()}View:")
    lines.append(f'    """Tests for {model} {view_type} view."""')
    lines.append("")
    
    url_name = f"{app_name}:{model_snake}_{view_type}"
    
    if view_type == "list":
        # List view tests
        lines.append("    def test_get_success(self, client):")
        lines.append(f'        """Test list view returns 200."""')
        lines.append(f'        url = reverse("{url_name}")')
        lines.append("        response = client.get(url)")
        lines.append("        assert response.status_code == 200")
        lines.append("")
        
        lines.append(f"    def test_empty_list(self, client):")
        lines.append(f'        """Test list view with no objects."""')
        lines.append(f'        url = reverse("{url_name}")')
        lines.append("        response = client.get(url)")
        lines.append("        assert response.status_code == 200")
        lines.append(f'        assert "{model_plural}" in response.context or "object_list" in response.context')
        lines.append("")
        
        lines.append(f"    def test_with_objects(self, client, {model_snake}):")
        lines.append(f'        """Test list view with objects."""')
        lines.append(f'        url = reverse("{url_name}")')
        lines.append("        response = client.get(url)")
        lines.append("        assert response.status_code == 200")
        
        if with_htmx:
            lines.append("")
            lines.append("    def test_htmx_request(self, client):")
            lines.append(f'        """Test HTMX request returns partial template."""')
            lines.append(f'        url = reverse("{url_name}")')
            lines.append('        response = client.get(url, HTTP_HX_REQUEST="true")')
            lines.append("        assert response.status_code == 200")
            lines.append("        # Should use partial template")
            lines.append('        assert "partial" in response.template_name[0] or response.template_name[0].endswith("_partial.html")')
    
    elif view_type == "detail":
        lines.append(f"    def test_get_success(self, client, {model_snake}):")
        lines.append(f'        """Test detail view returns 200."""')
        lines.append(f'        url = reverse("{url_name}", kwargs={{"pk": {model_snake}.pk}})')
        lines.append("        response = client.get(url)")
        lines.append("        assert response.status_code == 200")
        lines.append(f'        assert response.context["{model_snake}"] == {model_snake}')
        lines.append("")
        
        lines.append("    def test_not_found(self, client):")
        lines.append(f'        """Test 404 for non-existent object."""')
        lines.append(f'        url = reverse("{url_name}", kwargs={{"pk": 99999}})')
        lines.append("        response = client.get(url)")
        lines.append("        assert response.status_code == 404")
    
    elif view_type == "create":
        client_fixture = "authenticated_client" if with_permissions else "client"
        
        lines.append(f"    def test_get_form(self, {client_fixture}):")
        lines.append(f'        """Test create form is displayed."""')
        lines.append(f'        url = reverse("{url_name}")')
        lines.append(f"        response = {client_fixture}.get(url)")
        lines.append("        assert response.status_code == 200")
        lines.append('        assert "form" in response.context')
        lines.append("")
        
        lines.append(f"    def test_post_valid(self, {client_fixture}):")
        lines.append(f'        """Test creating with valid data."""')
        lines.append(f'        url = reverse("{url_name}")')
        lines.append(f"        data = {{'name': 'New {model}'}}")
        lines.append(f"        response = {client_fixture}.post(url, data)")
        lines.append("        assert response.status_code in [200, 302]  # Redirect on success")
        lines.append(f"        assert {model}.objects.filter(name='New {model}').exists()")
        lines.append("")
        
        lines.append(f"    def test_post_invalid(self, {client_fixture}):")
        lines.append(f'        """Test creating with invalid data."""')
        lines.append(f'        url = reverse("{url_name}")')
        lines.append("        data = {}  # Missing required fields")
        lines.append(f"        response = {client_fixture}.post(url, data)")
        lines.append("        assert response.status_code in [200, 422]")
        lines.append('        assert response.context["form"].errors')
        
        if with_htmx:
            lines.append("")
            lines.append(f"    def test_htmx_post_invalid(self, {client_fixture}):")
            lines.append(f'        """Test HTMX returns 422 on validation error."""')
            lines.append(f'        url = reverse("{url_name}")')
            lines.append("        data = {}")
            lines.append(f'        response = {client_fixture}.post(url, data, HTTP_HX_REQUEST="true")')
            lines.append("        assert response.status_code == 422")
    
    elif view_type == "update":
        client_fixture = "authenticated_client" if with_permissions else "client"
        
        lines.append(f"    def test_get_form(self, {client_fixture}, {model_snake}):")
        lines.append(f'        """Test update form is displayed with object data."""')
        lines.append(f'        url = reverse("{url_name}", kwargs={{"pk": {model_snake}.pk}})')
        lines.append(f"        response = {client_fixture}.get(url)")
        lines.append("        assert response.status_code == 200")
        lines.append('        assert "form" in response.context')
        lines.append(f'        assert response.context["object"] == {model_snake}')
        lines.append("")
        
        lines.append(f"    def test_post_valid(self, {client_fixture}, {model_snake}):")
        lines.append(f'        """Test updating with valid data."""')
        lines.append(f'        url = reverse("{url_name}", kwargs={{"pk": {model_snake}.pk}})')
        lines.append(f"        data = {{'name': 'Updated {model}'}}")
        lines.append(f"        response = {client_fixture}.post(url, data)")
        lines.append("        assert response.status_code in [200, 302]")
        lines.append(f"        {model_snake}.refresh_from_db()")
        lines.append(f"        assert {model_snake}.name == 'Updated {model}'")
    
    elif view_type == "delete":
        client_fixture = "authenticated_client" if with_permissions else "client"
        
        lines.append(f"    def test_get_confirm(self, {client_fixture}, {model_snake}):")
        lines.append(f'        """Test delete confirmation page."""')
        lines.append(f'        url = reverse("{url_name}", kwargs={{"pk": {model_snake}.pk}})')
        lines.append(f"        response = {client_fixture}.get(url)")
        lines.append("        assert response.status_code == 200")
        lines.append("")
        
        lines.append(f"    def test_post_delete(self, {client_fixture}, {model_snake}):")
        lines.append(f'        """Test deleting object."""')
        lines.append(f"        pk = {model_snake}.pk")
        lines.append(f'        url = reverse("{url_name}", kwargs={{"pk": pk}})')
        lines.append(f"        response = {client_fixture}.post(url)")
        lines.append("        assert response.status_code in [200, 302]")
        lines.append(f"        assert not {model}.objects.filter(pk=pk).exists()")
        
        if with_htmx:
            lines.append("")
            lines.append(f"    def test_htmx_delete(self, {client_fixture}, {model_snake}):")
            lines.append(f'        """Test HTMX delete returns trigger header."""')
            lines.append(f"        pk = {model_snake}.pk")
            lines.append(f'        url = reverse("{url_name}", kwargs={{"pk": pk}})')
            lines.append(f'        response = {client_fixture}.delete(url, HTTP_HX_REQUEST="true")')
            lines.append("        assert response.status_code == 200")
            lines.append('        assert "HX-Trigger" in response.headers')
    
    return "\n".join(lines)


@mcp.tool()
def generate_conftest(
    app_name: str,
    models: list[str],
    with_users: bool = True,
) -> str:
    """
    Generiert pytest conftest.py mit gemeinsamen Fixtures.
    
    Args:
        app_name: Django App Name
        models: Liste von Model Names
        with_users: User Fixtures generieren
        
    Returns:
        Python Code für conftest.py
    """
    imports = [
        "import pytest",
    ]
    
    for model in models:
        imports.append(f"from {app_name}.models import {model}")
    
    lines = []
    lines.append("\n".join(sorted(set(imports))))
    lines.extend(["", ""])
    
    if with_users:
        lines.extend([
            "@pytest.fixture",
            "def user(db, django_user_model):",
            '    """Create a regular user."""',
            "    return django_user_model.objects.create_user(",
            "        username='testuser',",
            "        email='test@example.com',",
            "        password='testpass123'",
            "    )",
            "",
            "",
            "@pytest.fixture",
            "def admin_user(db, django_user_model):",
            '    """Create an admin user."""',
            "    return django_user_model.objects.create_superuser(",
            "        username='admin',",
            "        email='admin@example.com',",
            "        password='adminpass123'",
            "    )",
            "",
            "",
            "@pytest.fixture",
            "def authenticated_client(client, user):",
            '    """Client logged in as regular user."""',
            "    client.force_login(user)",
            "    return client",
            "",
            "",
            "@pytest.fixture",
            "def admin_client(client, admin_user):",
            '    """Client logged in as admin."""',
            "    client.force_login(admin_user)",
            "    return client",
            "",
            "",
        ])
    
    for model in models:
        model_snake = snake_case(model)
        lines.extend([
            "@pytest.fixture",
            f"def {model_snake}(db):",
            f'    """Create a {model} instance."""',
            f"    return {model}.objects.create(name='Test {model}')",
            "",
            "",
        ])
    
    return "\n".join(lines)
