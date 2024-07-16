import os
import re
import carb
import omni
import omni.client
import omni.client.utils as clientutils


class Utils:
    USD_RE = re.compile("^.*\\.(usd([a-z])?|abc)(\\?.*)?$", re.IGNORECASE)

    @staticmethod
    def is_usd(path):
        if Utils.USD_RE.match(path):
            return True

        return False

    @staticmethod
    def compute_absolute_path(base_path, is_base_path_folder, path, is_path_folder):
        if is_base_path_folder and not base_path.endswith("/"):
            base_path += "/"

        if is_path_folder and not path.endswith("/"):
            path += "/"

        return clientutils.make_absolute_url_if_possible(base_path, path)

    @staticmethod
    def make_relative_path(relative_to, path):
        return clientutils.make_relative_url_if_possible(relative_to, path)

    @staticmethod
    def remove_prefix(text, prefix):
        if text.startswith(prefix):
            return text[len(prefix) :]

        return text

    @staticmethod
    def is_folder(path):
        result, entry = omni.client.stat(path)
        return result == omni.client.Result.OK and entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN

    @staticmethod
    async def list_folder_async(folder_path):
        absolute_paths = []
        relative_paths = []
        result, entry = await omni.client.stat_async(folder_path)
        if result == omni.client.Result.OK and entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
            is_folder = True
        else:
            is_folder = False

        folder_path = clientutils.make_file_url_if_possible(folder_path)
        if not is_folder:
            absolute_paths = [folder_path]
            relative_paths = [os.path.basename(folder_path)]
        else:
            if not folder_path.endswith("/"):
                folder_path += "/"

            folder_queue = [folder_path]
            while len(folder_queue) > 0:
                folder = folder_queue.pop(0)
                carb.log_info(f"Listing folder {folder}...")
                (result, entries) = await omni.client.list_async(folder)
                if result != omni.client.Result.OK:
                    break
                folders = set((e.relative_path for e in entries if e.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN))
                for f in folders:
                    folder_queue.append(Utils.compute_absolute_path(folder, True, f, False))
                files = set((e.relative_path for e in entries if not e.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN))
                for file in files:
                    absolute_path = Utils.compute_absolute_path(folder, True, file, False)
                    absolute_paths.append(absolute_path)
                    relative_path = Utils.remove_prefix(absolute_path, os.path.dirname(folder_path[:-1]))
                    relative_path = relative_path.replace("\\", "/")
                    if relative_path != "/" and relative_path.startswith("/"):
                        relative_path = relative_path[1:]
                    if len(relative_path) > 0:
                        relative_paths.append(relative_path)

        return absolute_paths, relative_paths

    @staticmethod
    def make_valid_identifier(identifier):
        if len(identifier) == 0:
            return "_"

        result = identifier[0]
        if not identifier[0].isalpha():
            result = "_"

        for i in range(len(identifier) - 1):
            if identifier[i + 1].isalnum():
                result += identifier[i + 1]
            else:
                result += "_"

        return result
