import ast
import sys
import angle
import english_parser
import nodes
import the
class Reflector(object):
    def __getitem__(self, name):
        if name=="__tracebackhide__":
            return False # for py.test
        print("Reflector __getitem__ %s" % str(name))
        if name in the.params:
            the.result= english_parser.do_evaluate(the.params[name])
        elif name in the.variables:
            the.result= english_parser.do_evaluate(the.variables[name].value)
        elif name in the.methods:
            return the.methods[name]
        else: raise Exception("UNKNOWN ITEM %s" % name)
        return the.result

    def __setitem__(self, key, value):
        import the
        print("Reflector __setitem__ %s %s" % (key, value))
        if key in the.variables:
            the.variables[key].value = value
        else:
            the.variables[key] = nodes.Variable(name=key, value=value)
        the.variableValues[key] = value
        the.result = value



class PrepareTreeVisitor(ast.NodeTransformer):
    def generic_visit(self, node):
        if not isinstance(node,ast.AST):
            return node
        for field, old_value in ast.iter_fields(node):
            old_value = getattr(node, field, None)
            if isinstance(old_value, list):
                new_values = []
                for value in old_value:
                    value = self.visit(value)
                    if value is None:
                        continue
                    elif not isinstance(value, ast.AST):
                        new_values.extend(value)
                        continue
                    new_values.append(value)
                old_value[:] = new_values
                setattr(node, field, old_value)
            else:
                new_node = self.visit(old_value)
                if new_node is None:
                    delattr(node, field)
                else:
                    setattr(node, field, new_node)
        return node

        # emitters.kast_emitter.wrap_value(val)
    def visit_list(self, x): # conflict: if isinstance(old_value, list): wrap before!
        return ast.List(x,ast.Load())
        # return kast.List(map(wrap_value,val),ast.Load())
    def visit_float(self, x):
        return ast.Num(x)
    def visit_str(self, x):
        return ast.Str(x)
    def visit_int(self, x):
        return ast.Num(x)
    def visit_Variable(self, x):
        return ast.Name(x.id,ast.Load())
        # x.ctx=ast.Load()
        # return x
        # def generic_visit(self, node):


# Module(body=[Expr(value=Num(n=1, lineno=1, col_offset=0), lineno=1, col_offset=0)])
# Module([Expr(Num(1))])
def eval_ast(my_ast, args={}, source_file='file',target_file=None):
    import codegen
    import ast
    import the

    try:  # todo args =-> SETTERS!
        # context_variables=variableValues.copy()+globals()+locals()
        the.params = the.variableValues.copy()
        the.params.update(args)
        # context_variables.update(globals())
        # context_variables.update(locals())

        variable_inits = []
        # for k in args:
        #     s = kast.setter(k, do_evaluate(args[k]))
        #     variable_inits.append(s)
        # elif args:my_ast.body=variable_inits+my_ast.body

        # gotta wrap: 1 => Module(body=[Expr(value=[Num(n=1)])])
        if not type(my_ast) == ast.Module:
            # my_ast = flatten(my_ast)
            if not isinstance(my_ast,ast.Expr):
                my_ast = [ast.Expr(my_ast)]
            my_ast = ast.Module(body=variable_inits + my_ast)
        PrepareTreeVisitor().visit(my_ast)
        print(my_ast.body)
        source = codegen.to_source(my_ast)
        print(source)  # => CODE
        print ast.dump(my_ast)
        my_ast = ast.fix_missing_locations(my_ast)
        code = compile(my_ast, source_file, 'exec')
        # TypeError: required field "lineno" missing from expr NONO,
        # this as a documentation bug,
        # this error can mean >>anything<< except missing line number!!! :) :( :( :(

        # code=compile(my_ast, 'file', 'exec')
        # eval can't handle arbitrary python code (eval("import math") ), and
        # exec() doesn't return the results.
        if target_file:
            import ast_export
            ast_export.emit_pyc(code,target_file)
        if angle.use_tree:
            the.result=my_ast
            return my_ast# code #  Don't evaluate here

        ret = eval(code, the.params, Reflector())
        ret = ret or the.result
        print("GOT RESULT %s" % ret)
        # err= sys.stdout.getvalue()
        # if err: raise err
        # z=exec (code)
        the.params.clear()
        return ret
    except Exception as e:
        print(my_ast)
        # ast.dump(my_ast)
        raise e, None, sys.exc_info()[2]
