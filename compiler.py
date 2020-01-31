import re
import io

def frmt_func5(match):
    return match.groups()[0]

# return the same line without starting or ending indents or spaces
def remove_indents_spaces(ln):
    return re.sub(r'\s*\t*(.*)\s*\t*', frmt_func5, ln)


# auxalary: evaluate match of RegEx
def frmt_func2(match):
    return match.groups()[0]


# removes the { % % } {[} so it will be regular python code
def format_ctrl_structures(ln):
    return re.sub(r'\s*{%\s*(.*?)\s*%}\s*{\[}\s*', frmt_func2, ln)


# auxalary: evaluate match of RegEx
def frmt_func1(match):
    return '{}'


# replaces the {{ parameter }} in {} so it will be used for .format
def format_expressions(ln):
    return re.sub(r'{{\s*(.*?)\s*}}\s*', frmt_func1, ln)

# returns all parameters from  {{ parameter1 }}  {{ parameter2 }}
# so it will be used for .format as arguments
def get_arguments(ln):
    return re.findall(r'{{\s*(.*?)\s*}}', ln)


# replace parameters with their values from the parameters dict
# (which will be composed of HTTP GET parameters)
def deparameterise(ln, params):
    pattern = r'\b({})\b'.format('|'.join(sorted(re.escape(p) for p in params)))
    deline = re.sub(pattern, lambda m: str(params.get(m.group(0))), ln)
    formated = remove_indents_spaces(deline)
    return formated

# indent function to indent all the lines of a string
# which represents python code
def indent(ln, indents_num):
    return (indents_num * '\t') + ln


# this function gets a dynamic-syntax html code of some control structure type:
# for, if, while and retorns the pycode,
# which generates a non-dynamic html after using that control structure
def start_control_structure(ctrl_struct):
    return format_ctrl_structures(ctrl_struct)


# removes the { % % } {[} so it will be regular python code
def format_command(ln):
    return re.sub(r'{%\s*(.*?)\s*%}\s*$', frmt_func2, ln)

# this function gets a dynamic-syntax html code of some control structure type:
# for, if, while and retorns the pycode,
# which generates a non-dynamic html after using that control structure
def start_command(ctrl_struct):
    return format_command(ctrl_struct)

# this function gets a dynamic-syntax html code of some expression type:
# like {{ user_name }} which should be evaluated for example to Alex
# which generates a non-dynamic html after using that control structure
def expr_code_gen(ln, v_i, indents_num):
    formated_line = format_expressions(ln)
    arguments_array = get_arguments(ln)
    arguments_array_string = '['
    for i, s in enumerate(arguments_array):
        arguments_array_string += s
        if not i == len(arguments_array)-1:
            arguments_array_string += ', '
    arguments_array_string += ']'

    return indent('text' + str(v_i) + '= \'' + formated_line + '\'' + '.format(*' + \
        arguments_array_string + ')' + '\n', indents_num) + \
        indent('html_holder.append(text' + str(v_i) + ')' + '\n', indents_num)

def compute_code(dynamic_html, parameters):
    # RegEx for the given dynamic html syntax
    flow_control = '{%.*%}\s*{\[}\s*'
    command = '{%.*%}\s*$'
    block_end = '\s*{]}\s*'
    expression = '\s*{{.*}}\s*'
    opened_tag = '\s*<[^\/].*>\s*'
    closed_tag = '\s*</.*>\s*'
    empty_line = '^\s*$'

    '''
    py_code is a string which represents the builded python code, 
    running which will result in creating a non-dynamic html page
     from dynamic html page'''

    py_code = 'html_holder=[]'+'\n'
    # it hold a list of html code lines which represent the non-dynamic html code

    # py_indents_num is a counter which will count number of indentations to format my py_code correctfully
    py_indents_num = 0
    # html_indents_num is a counter which will count number of indentations to format my html_code correctfully
    # which will be injected also as string variables called text_i which I will push into the html_holder
    html_indents_num = 0
    # the i of the text_i identifier which used to create new variables
    # called text_i which will hold non-dynamic html code
    var_i = 0
    # text constant string
    text = 'text'

    # used to create html in each iteration on the dynamic html lines from the file
    cur_html = ''

    with io.StringIO(dynamic_html) as fp:
        for line in fp:
            # if empty continue
            if line == '\n' or re.search(empty_line, line):
                continue
            # replace parameters which are given in the parameters dict
            # if none no changes
            dp_line = deparameterise(line, parameters)
            if re.search(command, line):
                command_start_pycode = start_command(dp_line)
                # increase identifier
                var_i += 1
                py_code += indent(command_start_pycode, py_indents_num) + '\n'
            # if it is {{ % structure flow % } {[}
            elif re.search(flow_control, line):
                # create structure flow whithout { % % }
                control_start_pycode = start_control_structure(
                    dp_line)
                # increase identifier
                var_i += 1
                # indent created code with correct py_indents_num
                py_code += indent(control_start_pycode, py_indents_num) + '\n'
                # increase it because of a new control structure and its block started
                py_indents_num += 1
            # if it is {]} block closed
            elif re.search(block_end, line):
                # decrease it because the block ended and closed
                py_indents_num -= 1
            # if it is {{ user_name }} {{ parameter34 }} one expression or more
            elif re.search(expression, dp_line):
                # create code for expression
                expr_pycode = expr_code_gen(indent(dp_line, html_indents_num), var_i, py_indents_num)
                py_code += expr_pycode
                # increase used indentifier
                var_i += 1
            # else it is some html tags
            else:
                if re.search(closed_tag, line):
                    html_indents_num -= 1
                # create text_i with the html and
                # add the html code to the html_holder
                py_cur_code = indent('text' + str(var_i) + '=' + '\'', py_indents_num) + \
                              indent(dp_line, html_indents_num) + '\'' + '\n'
                py_cur_code += indent('html_holder.append(text' + str(var_i) + ')', py_indents_num) + '\n'
                # add it to the generated python code
                py_code += py_cur_code
                # increase variable text identifier
                var_i += 1
                if re.search(opened_tag, line):
                    html_indents_num += 1
                # not used now, but this wll be used to format the html code ether

    py_code += '''
html_string = ''
for html_line in html_holder:
    html_string += html_line
'''
    return py_code