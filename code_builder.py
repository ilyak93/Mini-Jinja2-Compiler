import compiler

class CodeBuilder(object):
    """ Build source code """
    def __init__(self, filepath, parameters):
        with open(filepath, 'r') as file:
            self.dynamic_html = file.read()
        self.params = {}
        for param in parameters:
            self.params[param] = parameters[param]

    def get_globals(self):
        """Execute the code, and return a dict of globals it defines."""
        # Get the Python source as a single string.
        python_source = compiler.compute_code(self.dynamic_html, self.params)
        # Execute the source, defining globals, and return them.
        html_holder = {}
        await exec(python_source, html_holder)
        html_string = html_holder['html_string']
        return html_string