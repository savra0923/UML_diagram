import _ast, ast
import argparse
import os.path
import os
import sys
import pydot

class DependencyDotGenerator:
    # This class is adopted from https://gist.github.com/hsun/2991630 which I heavily modified
    """
    This class creates a DOT file based on the given dependencies.

    Attributes:
        print_classes: Prints all classes into the Dot file.
        print_relations: Prints all relations between classes into the Dot file.
        print_imp_relations: Prints all import relations between classes into the Dot file.
    """

    def render(self, dependencies, order, relation, imp_relations, output=None):
        """
        Create input for DOT, and writes into it.

        Parameters
        ----------
        dependencies: Dictionary of class dependencies.
        order: Dictionary of numbered class dependencies.
        relation: Dictionary of relations between classes dependencies.
        imp_relations: Dictionary of import relations between class dependencies.
        output: Location of output file

        """

        f = open(output, 'w', encoding='utf-8') if output else sys.stdout

        f.write('digraph G {\n')
        f.write('ranksep=1.0;\n')
        f.write('node [style=filled,fontname=Helvetica,fontsize=10];\n')

        self.print_classes(f, dependencies)
        self.print_relations(f, relation, order)
        self.print_imp_relations(f, imp_relations, order)

        f.write('}\n')
        f.close()

    def print_classes(self, f, dependencies):
        """
        Prints all classes information into the dot file.

        Parameters
        ----------
        f: The Dot file we are writing into
        dependencies: Dictionary of class dependencies.

        """
        for m, deps in dependencies.items():
            for d in deps:
                f.write('%s' % (self.fix(d)))
                f.write(';\n')
        return

    def print_relations(self, f, relation, order):
        """
        Prints all classes relations into the dot file.

        Parameters
        ----------
        f: The Dot file we are writing into
        dependencies: Dictionary of relations between classes dependencies.
        order: Dictionary of numbered class dependencies.

        """
        for give, take in relation.items():
            if take not in order:
                continue
            f.write('"{0}" -> "{1}" [arrowhead="empty", arrowtail="none"];\n'.format(order[give], order[take]))
        return

    def print_imp_relations(self, f, relation, order):
        """
        Prints all import relations into the dot file.

        Parameters
        ----------
        f: The Dot file we are writing into
        relation: Dictionary of import relations between class dependencies..
        order: Dictionary of numbered class dependencies.

        """
        for num, list in relation.items():
            for item in list:
                if item in order:
                    f.write('"{0}" -> "{1}" [arrowhead="empty", arrowtail="none"];\n'.format(order[item], num))
        return

    def fix(self, s):
        """
        Convert a module name to a syntactically correct node name
        Parameters
        ----------
        s: module name

        Returns
        -------
        correct node name
        """
        return s.split('.')[-1]

class ImportVisitor(ast.NodeVisitor):
    """
    This class visits AST tree and records all dependent modules from a package.

    Param:
        package_name: The current package

    Attributes:
        depgraph: Dependency graph which is a map like.
        package_name: The current package. We will only record modules in the given package.
        cur_module_name: Current module of the AST tree being visited
        counter: counter used to relate packages
        num_to_class: Dictionary corresponds classes to numbers (used for correct .dot file)
        depgRelation: Dictionary relation between classes
        verb_list Dictionary of each class and its variables
        import_relation: Dictionary relation between classes through imports
    """

    def __init__(self, package_name):
        """
        Inits ImportVisitor class.

        Parameters
        ----------
        package_name: The current package
        """
        self.depgraph = {}
        self.package_name = package_name
        # We will only record modules in the given package.

        self.cur_module_name = None
        # current module of the AST tree being visited

        self.counter=0
        self.num_to_class= {}
        # corrosponds classes to numbers (used for correct .dot file)

        self.depgRelation= {}
        self.verb_list= {}
        self.import_relation={}

    def add_dependency(self, depend_module):
        """
        adds dependency to depgraph

        Parameters
        ----------
        depend_module: the module to be added
        """
        self.depgraph.setdefault(self.cur_module_name, set()).add(depend_module)

    def visit(self, node):
        """
        This function visits the node is in the packages and extract the relevant information
        (i.e. classes, functions, variables, relations between them)
        Parameters
        ----------
        node: current node
        """
        if isinstance(node, _ast.ImportFrom):
            # AST definition:
            #     ImportFrom(identifier? module, alias* names, int? level)
            #     Gets import relation
            self.import_info(node)

        if isinstance(node, ast.ClassDef):
            self.class_info(node)
        elif isinstance(node, ast.Attribute):
            self.attribute_info(node)

    def import_info(self, node):
        """
        This function gets a node of type _ast.ImportFrom and saves all imports relations the class uses
        (where the import is also part of the project)

        Parameters
        ----------
        node: _ast.ImportFrom node we want the information from

        """
        for (fieldname, value) in ast.iter_fields(node):
            if fieldname == 'names':
                if value[0].name.startswith('Q') or value[0].name.islower() or value[0].name.isupper() or value[0].name == '*':
                    continue
                vlist = []

                # if the import is relevant add it to vlist
                if self.counter in self.import_relation:
                    vlist = self.import_relation[self.counter]
                if (value[0].name not in vlist):
                    vlist.append(value[0].name)
                    self.import_relation[self.counter] = vlist
        return

    def class_info(self, node):
        """
        This function gets a node of type _ast.ClassDef and saves all the class information.
        (i.e. class name, and methods in the class)

        Parameters
        ----------
        node: _ast.ClassDef node we want the information from

        """
        atr_list = ''
        atr_list = '"' + str(self.counter) + '" [label="{' + node.name + "| "

        methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
        for method in methods:
            if method == "__init__":
                attribute = {n.attr for n in ast.walk(node) if (
                        isinstance(n, ast.Attribute) and n.attr.startswith("_") and not n.attr.startswith("__"))}
                for a in attribute:
                    atr_list = atr_list + a + '\l'
                atr_list = atr_list + '| '
                continue
            elif method.startswith("__"):
                continue
            atr_list = atr_list + method + '()\l'

        atr_list = atr_list + '}", shape="record"]'

        self.num_to_class[node.name] = self.counter
        self.add_dependency(atr_list)
        self.verb_list[self.counter] = []
        self.counter += 1
        ids = [n.id for n in node.bases if hasattr(n, 'id')]

        for id in ids:
            self.depgRelation[node.name] = id
        return

    def attribute_info(self, node):
        """
        This function gets a node of type _ast.Attribute and saves all the attributes in the class class information.

        Parameters
        ----------
        node: _ast.Attribute node we want the information from

        """
        v_list = []

        if (self.counter - 1) in self.verb_list:
            v_list = self.verb_list[self.counter - 1]

        if (node.attr not in v_list):
            v_list.append(node.attr)
            self.verb_list[self.counter - 1] = v_list
        return

def set_up_files(output_path= "documentation/UML"):
    """
    This function creates the output location for the UML diagram (.dot file).
    Parameters
    ----------
    output_path: Path to folder, default =documentation/UML

    Returns
    -------
    The path location of the UML diagram (.dot file)
    """
    if not os.path.exists(output_path):
        p_sys = sys.path[0].split('documentation')[0]
        output_path = os.path.join(p_sys, output_path)
        if not os.path.exists(output_path):
            os.mkdir(output_path)

    file_loc= os.path.join(output_path, 'classes_blyzer.dot')

    return file_loc

def UML_generator(package_path= 'blyzer', output_path="documentation/UML"):
    """
    This function generates a UML diagram for the blyzer project.
    By default the project is 'blyzer' and the UMLs are saved in 'documentation/UML'.

    Parameters
    ----------
    package_path: Name of the project you wish to generate UML for.
    ouput_path: Location of saved UML
    """

    output_path = set_up_files(output_path)

    (_, package_name) = os.path.split(package_path)
    import_visitor = ImportVisitor(package_name)
    # Analyze all the .py files under this directory 'path'
    path_prefix_len = len(os.path.split(package_path)[0])
    for root, _, files in os.walk(package_path):
        module_prefix = ".".join(root[path_prefix_len + 1:].split('/'))
        for pyfile in files:
            if pyfile.endswith(".py"):
                module_name = ".".join([module_prefix, os.path.splitext(pyfile)[0]])
                import_visitor.cur_module_name = module_name
                ast_tree = ast.parse(open(os.path.join(root, pyfile), encoding='utf-8').read())

                for node in ast.walk(ast_tree):
                    import_visitor.visit(node)

    # Generates the UML diagram as .dot file
    dot_generator = DependencyDotGenerator()
    dot_generator.render(import_visitor.depgraph, import_visitor.num_to_class, import_visitor.depgRelation, import_visitor.import_relation, output_path)

    # Converts the .dot file to .png file
    (graph,) = pydot.graph_from_dot_file(output_path)
    graph.write_png(output_path.replace('.dot', '.png'))
    os.remove(output_path)


def main():
    """
    main method of UML_generator(), to be used as CLI interface.
    After verifying that enough arguments were passed and their validity,
    calls UML_generator.
    """
    parser = argparse.ArgumentParser(description='Build module dependency graph for a package.')
    parser.add_argument('-p', '--path', nargs='?', type=str, help='path to the top level package we want to analyze')
    parser.add_argument('-o', '--out',  nargs='?', type=str, help='output path, if missing, output is written to documentation/UML')
    args = parser.parse_args()

    if (args.path is None) and (args.out is None):
        UML_generator()
    elif args.out is None:
        UML_generator(args.path)
    else:
        UML_generator(args.path, args.out)

if __name__ == '__main__':
    main()
