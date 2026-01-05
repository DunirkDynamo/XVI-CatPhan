# Building Documentation with Sphinx

This guide explains how to build and maintain the Sphinx documentation for the CatPhan Analysis package.

## Prerequisites

Install Sphinx and required extensions:

```bash
pip install sphinx sphinx-rtd-theme
```

Or install all dependencies including documentation tools:

```bash
pip install -r requirements.txt
```

## Documentation Structure

```
docs/
├── conf.py              # Sphinx configuration
├── index.rst            # Main documentation page
├── installation.rst     # Installation guide
├── quickstart.rst       # Quick start guide
├── user_guide.rst       # Detailed user guide
├── api_reference.rst    # API documentation (auto-generated)
├── examples.rst         # Usage examples
├── Makefile             # Build file (Unix/Mac)
├── make.bat             # Build file (Windows)
├── _static/             # Static files (CSS, images, etc.)
├── _templates/          # Custom templates
└── _build/              # Generated documentation (created during build)
```

## Building Documentation

### On Windows

```bash
cd docs
make.bat html
```

### On Unix/Mac/Linux

```bash
cd docs
make html
```

### Viewing Built Documentation

After building, open the HTML documentation:

**Windows:**
```bash
start _build/html/index.html
```

**Mac:**
```bash
open _build/html/index.html
```

**Linux:**
```bash
xdg-open _build/html/index.html
```

## Sphinx Configuration

The documentation is configured in `docs/conf.py` with the following key settings:

### Extensions

- **sphinx.ext.autodoc**: Automatic API documentation from docstrings
- **sphinx.ext.napoleon**: Support for Google and NumPy style docstrings
- **sphinx.ext.viewcode**: Add links to highlighted source code
- **sphinx.ext.intersphinx**: Link to other project documentation
- **sphinx.ext.todo**: Support for TODO items
- **sphinx.ext.coverage**: Coverage statistics
- **sphinx.ext.mathjax**: Math rendering

### Theme

Uses the Read the Docs theme (`sphinx_rtd_theme`) for professional appearance.

### Autodoc Settings

Automatically documents:
- All class members
- Special methods like `__init__`
- Undocumented members
- Shows inheritance relationships

## Docstring Format

The package uses **Google-style docstrings**, which Sphinx can parse automatically:

```python
def example_function(param1, param2):
    """
    Brief description of the function.
    
    More detailed description here, with multiple paragraphs if needed.
    This can include usage examples.
    
    Args:
        param1 (str): Description of param1
        param2 (int): Description of param2
        
    Returns:
        bool: Description of return value
        
    Raises:
        ValueError: When param1 is invalid
        
    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
        True
    """
    return True
```

## Updating Documentation

### Adding New Pages

1. Create a new `.rst` file in the `docs/` directory
2. Add it to the `toctree` in `index.rst`:

```rst
.. toctree::
   :maxdepth: 2
   
   installation
   quickstart
   your_new_page
```

### Auto-Generating API Documentation

The API documentation is automatically generated from docstrings. To update:

1. Ensure your code has proper docstrings
2. The `api_reference.rst` uses `automodule` and `autoclass` directives
3. Rebuild documentation: `make html`

### Adding Examples

Add new examples to `docs/examples.rst` using code blocks:

```rst
Example: Your New Example
--------------------------

Description of what this example does.

.. code-block:: python

   from catphan_analysis import CatPhanAnalyzer
   
   # Your example code here
```

## Common Sphinx Commands

### Clean Build

Remove all built files and rebuild:

**Windows:**
```bash
make.bat clean
make.bat html
```

**Unix/Mac:**
```bash
make clean
make html
```

### Check Links

Verify all external links work:

```bash
make linkcheck
```

### Build PDF Documentation

Requires LaTeX installed:

```bash
make latexpdf
```

### Build Other Formats

Sphinx supports multiple output formats:

- `make html` - HTML website
- `make singlehtml` - Single HTML page
- `make latex` - LaTeX source
- `make latexpdf` - PDF via LaTeX
- `make epub` - EPUB ebook
- `make man` - Manual pages
- `make text` - Plain text

## Hosting Documentation

### Read the Docs

The documentation is ready to be hosted on [Read the Docs](https://readthedocs.org/):

1. Create account on readthedocs.org
2. Import your GitHub repository
3. Configure webhook (automatic)
4. Documentation builds automatically on each commit

### GitHub Pages

To host on GitHub Pages:

1. Build documentation:
   ```bash
   cd docs
   make html
   ```

2. Copy `_build/html/` contents to `docs/` or gh-pages branch

3. Enable GitHub Pages in repository settings

### Manual Hosting

The built HTML documentation in `docs/_build/html/` is a static website that can be hosted anywhere:

- Upload to web server
- Use S3 + CloudFront
- Host on Netlify or Vercel

## Troubleshooting

### "sphinx-build not found"

Install Sphinx:
```bash
pip install sphinx sphinx-rtd-theme
```

### Import Errors During Build

Sphinx needs to import your package. Ensure:

1. Package is installed: `pip install -e .`
2. Or add package path in `conf.py` (already configured)

### Docstrings Not Appearing

Check:

1. Docstrings use proper format (Google/NumPy style)
2. Methods/classes are actually documented
3. `autodoc` extension is enabled in `conf.py`
4. Module is properly imported in `api_reference.rst`

### Build Warnings

Review warnings carefully:
- Missing docstrings
- Invalid cross-references
- Formatting issues

Fix warnings to improve documentation quality.

## Best Practices

1. **Write docstrings as you code** - Don't wait until later
2. **Use Google-style docstrings** - Consistent format
3. **Include examples** - Show how to use features
4. **Build documentation regularly** - Catch issues early
5. **Keep documentation in sync with code** - Update on changes
6. **Add cross-references** - Link related sections
7. **Use type hints** - Helps with auto-documentation

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/docs.yml`:

```yaml
name: Documentation

on: [push, pull_request]

jobs:
  docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Build documentation
        run: |
          cd docs
          make html
      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main'
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: ./docs/_build/html
```

## Quick Reference

### Build Commands

```bash
# Windows
cd docs
make.bat html        # Build HTML
make.bat clean       # Clean build
make.bat linkcheck   # Check links

# Unix/Mac/Linux
cd docs
make html           # Build HTML
make clean          # Clean build
make linkcheck      # Check links
```

### View Documentation Locally

After building, the documentation is at:
```
docs/_build/html/index.html
```

### Rebuild After Changes

```bash
cd docs
make clean && make html
```

## Summary

Your CatPhan Analysis package is now **fully configured for Sphinx autodocumentation**:

✅ Complete Sphinx configuration (`conf.py`)  
✅ Documentation structure with multiple pages  
✅ API reference with autodoc directives  
✅ Napoleon extension for Google-style docstrings  
✅ Read the Docs theme  
✅ Build scripts for Windows and Unix  
✅ Requirements updated with Sphinx dependencies  

**To build documentation:**

```bash
cd docs
make.bat html  # Windows
# or
make html      # Unix/Mac
```

Then open `docs/_build/html/index.html` in your browser!
