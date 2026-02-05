# Makefile for Sphinx documentation - DDL Governance

SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

.PHONY: help clean html

help:
	@echo "DDL Governance Documentation"
	@echo ""
	@echo "  make html     - Build HTML documentation"
	@echo "  make clean    - Remove build directory"

clean:
	rm -rf $(BUILDDIR)

html:
	$(SPHINXBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html
	@echo ""
	@echo "Build finished. Open $(BUILDDIR)/html/index.html"
