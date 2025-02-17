import os
import re


def function_purification(code: str, skip_loc_threshold=False) -> str:
    # remove comments
    code = re.sub('\/\*[\w\W]*?\*\/', "", code)
    code = re.sub(r'//.*?\n', "\n", code)
    # remove non-ASCII
    code = re.sub(r"[^\x00-\x7F]+", "", code)
    # remove #
    code = re.sub(r"^#.*", "", code, flags=re.MULTILINE)
    # Counting ; as a way to see how many code lines, We do not consider very short functions
    if not skip_loc_threshold and code.count(";") <= 3:
        return ""
    # remove the empty line to compact the code
    purified_code_lines = list(filter(lambda c: len(c.strip()) != 0, code.split("\n")))
    # Counting the line which blank or contain only 1 char, We do not consider very short functions
    loc = 0
    for i in range(len(purified_code_lines)):
        purified_code_lines[i] = purified_code_lines[i].strip()
        loc += 1 if len(purified_code_lines[i]) > 1 else 0
    if not skip_loc_threshold and loc <= 5:
        return ""
    return "\n".join(purified_code_lines)


def abs_listdir(directory: str):
    return [os.path.join(directory, path) for path in os.listdir(directory)]

def get_function_body(current_code, start_line):
    open_brackets = 0
    open_parentheses = 0  # 用于跟踪参数部分中的括号
    in_function = False
    in_string = False
    in_comment = False
    end_line = start_line
    param_mode = True  # 表示是否还在参数部分
    function_start = None
    function_body = ""

    for i in range(start_line, len(current_code)):
        line = current_code[i].strip()
        if i == start_line:
            function_start = line.find("function")
            if function_start != -1:
                line = line[function_start:]
        j = 0
        while j < len(line):
            char = line[j]
            function_body += char
            # 处理单行注释 "//" 或 "#"
            if not in_string and not in_comment and ((j < len(line) - 1 and line[j:j+2] == '//') or line[j] == '#'):
                function_body += line[j+1:]
                break
            
            # 处理多行注释开始
            if not in_string and j < len(line) - 1 and line[j:j+2] == '/*':
                in_comment = True
                function_body += line[j+1]
                j += 2
                continue
            # 处理多行注释结束
            if in_comment and j < len(line) - 1 and line[j:j+2] == '*/':
                in_comment = False
                function_body += line[j+1]
                j += 2
                continue

            # 跳过注释内容
            if in_comment:
                j += 1
                continue

            # 处理字符串
            if char in ('"', "'") and not in_comment:
                if in_string:
                    if char == in_string:  # 结束当前字符串
                        in_string = False
                else:
                    in_string = char  # 开始一个新的字符串
                j += 1
                continue

            # 跳过字符串内容
            if in_string:
                j += 1
                continue

            # 在函数参数部分跟踪圆括号
            if param_mode:
                if char == '(':
                    open_parentheses += 1
                elif char == ')':
                    open_parentheses -= 1
                    # 当所有圆括号都匹配后，参数部分结束
                    if open_parentheses == 0:
                        param_mode = False
                j += 1
                continue

            # 计数函数体中的大括号
            if not param_mode:
                if char == '{':
                    if not in_function:
                        in_function = True  # 确保这是函数体的第一个大括号
                    open_brackets += 1
                elif char == '}':
                    open_brackets -= 1

            # 如果括号平衡为0，表示函数结束
            if in_function and open_brackets == 0:
                end_line = i
                return function_body, end_line

            j += 1
        function_body += '\n'
    return function_body, end_line

