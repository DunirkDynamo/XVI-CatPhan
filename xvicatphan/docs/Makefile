# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?= # This is an empty variable for "options." 
                 # The ?= means "set this only if it isn't already set."
                 # You could use this to pass extra flags (like "warnings as errors").
SPHINXBUILD   ?= sphinx-build # This defines the actual command that runs Sphinx. 
                              #If you have multiple versions of Sphinx, you could change this to a specific path.
SOURCEDIR     = . # Tells the script that your .rst files are in the current directory (the docs/ folder).
BUILDDIR      = _build # This is where the built documentation will go.


# Put it first so that "make" without argument is like "make help".
# In a Makefile, the first instruction is the one that runs by default.
# If you just type make in your terminal, it runs this help command.
# The @ symbol tells the terminal "don't print the command itself,
# just show the result."
# It asks Sphinx to list all the things you can build (html, pdf, epub, etc.).
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
