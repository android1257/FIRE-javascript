import json
import os
import random
import shutil
import subprocess
from typing import List

from loguru import logger

import Dataset.base
import Dataset.utils


class ProjectDataset(Dataset.base.BaseDataset):
    """
    Dataset of the target function to detect
    """

    def _preprocess(self, project_dir):
        logger.info("Preprocessing Target Function Dataset")
        logger.info(f"Extracting function from {project_dir} to {self.cache_dir}")

        cmd = (f'{self.path_to_ctags} -R --kinds-JavaScript=f -u --fields=-fP+ne --language-force=JavaScript'
               f' --output-format=json -f - "{project_dir}"')
        logger.debug(f"{cmd}")
        all_function_list_str = subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True).decode(
            errors="ignore")

        current_file = ""
        current_code = []
        all_function_list = all_function_list_str.split("\n")
        self.total_functions = len(all_function_list)  # All function including those < 3 lines
        for line in all_function_list:
            if not line.strip(): 
                continue
            if line.startswith("ctags: Notice: "): # ctags warning
                continue
            try:
                info = json.loads(line)
            except BaseException as e:
                logger.error(f"Error {e} When Parsing Ctag info: ", line)
                continue
            if info["path"] != current_file:
                ext = os.path.splitext(info["path"])[1].lower()
                if ext not in [".js", ".cjs", ".mjs", ".jsx"]:
                    continue
                try:
                    with open(info["path"]) as f:
                        current_code = f.read().split("\n")
                    current_file = info["path"]
                except:
                    logger.warning(f"Fail to Parse Function in {info['path']}")
                    continue
            # Get Function Range
            start_line = info["line"] - 1
            # Find the end line of the function
            func_body, end_line = Dataset.utils.get_function_body(current_code, start_line)

            if end_line >= len(current_code):
                logger.warning(f"Function end not found in {info['path']}")
                continue
            # Reconstruct function declaration since sometimes they are something missing
            func_lines = func_body.split("\n")
            try:
                first_line = func_lines[0]
                func_bracket_pos = first_line.find("(")
                func_lines[0] = f"function {info['name']}{first_line[func_bracket_pos:]}"
                # Or we'll give up Reconstructing Declaration
            except Exception as e:
                logger.warning("Function Declaration Parse Error: {}".format(e))
            func_body = "\n".join(func_lines)
            # function_body purification
            func_body = Dataset.utils.function_purification(func_body, self.skip_loc_threshold)
            if func_body == "":
                continue
            # ConstructPath
            relative_path = os.path.relpath(info["path"], project_dir)
            function_file_name = info["name"] + "@@@" + "@#@".join(relative_path.split("/"))
            function_file_name = function_file_name.replace("/", "%2F")
            function_file_name = function_file_name.replace("%", "%25")

            target_file = os.path.join(self.cache_dir, function_file_name)
            logger.debug(f"writing function to {target_file}")
            with open(target_file, "w") as f:
                f.write(func_body)
        logger.info("Target Function Preprocessing Finished")

    def __init__(self, project_dir: str, seed=20231031, rebuild=False, skip_loc_threshold=False, restore_processed=False):
        """
        Initialize Project dataset
        :param project_dir: Path to the folder of Target Project Dataset
        :param seed: seed for random
        """
        super().__init__(project_dir, seed)
        self.func_path_list = []
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        self.path_to_ctags = os.path.join(cur_dir, "universal-ctags/ctags")
        self.skip_loc_threshold = skip_loc_threshold
        self.restore_processed = restore_processed

        if not os.path.exists(self.path_to_ctags):
            logger.critical("Ctags Not Found In Given Path")
            raise Exception("Ctags Not Found In Given Path")
        if not os.path.exists(project_dir):
            logger.critical("The target Project Path is Not Exist")
            raise Exception("The target Project Path is Not Exist")

        logger.info("Initializing Project Dataset")
        project_name = os.path.split(project_dir.rstrip("/"))[-1]
        self.cache_dir = os.path.join(os.curdir, "processed", project_name)
        if rebuild or not (os.path.exists(self.cache_dir) and len(os.listdir(self.cache_dir)) != 0):
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            os.makedirs(self.cache_dir, exist_ok=True)
            self._preprocess(project_dir)
        else:
            if not (os.path.exists(self.cache_dir) and len(os.listdir(self.cache_dir)) != 0):
                os.makedirs(self.cache_dir, exist_ok=True)
                self._preprocess(project_dir)
            else:
                logger.info("Using Target_Function preprocessed Cache")
        logger.info(f"Project Dataset Size: {len(os.listdir(self.cache_dir))}")

    def __del__(self):
        if not self.restore_processed:
            shutil.rmtree(self.cache_dir, ignore_errors=True)

    def get_funcs(self, size=-1, **kwargs) -> List[str]:
        """
        Get the function list of the Project dataset.
        :param size: Size of the return function list.
        :return: The function list.
        """
        if size != -1:
            rng = random.Random(self.seed)
            func_path_list = rng.sample(Dataset.utils.abs_listdir(self.cache_dir),
                                        min(size, len(self.func_path_list)))
        else:
            func_path_list = Dataset.utils.abs_listdir(self.cache_dir)
        return func_path_list