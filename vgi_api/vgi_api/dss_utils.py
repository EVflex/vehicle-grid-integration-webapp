import glob
import os
import re
import logging

"""
Utility functions for handling dss files.
"""


def changeDirectorySeparatorStyle(folder, verbose=False):
    """
    Utility function to change Windows-style directory separators (\) to that used by Mac/Linux (/).
    All .dss and .txt files within the folder (and subfolder) will be edited.
    """

    # All .dss files currently use Windows-style separators; can skip if that style is needed
    if os.path.sep == "\\":
        return

    # Get list of dss and txt files
    dt_files = glob.glob(
        os.path.join(folder, "**", "*.dss"), recursive=True
    ) + glob.glob(os.path.join(folder, "**", "*.txt"), recursive=True)

    if verbose:
        logging.info(
            "\nPreparing to edit directory separators used in {}...".format(folder)
        )

    # Open every file and rewrite with \->/ if needed
    for dt_file in dt_files:
        with open(dt_file, "r+") as f:
            contents = f.read()

            old_contents = contents
            contents, substitutions = re.subn(r"\\(?! )", r"/", contents)

            if substitutions:
                f.seek(0)
                f.write(contents)
                f.truncate()
                if verbose:
                    logging.info("Edited %s", os.path.relpath(dt_file, start=folder))

    if verbose:
        logging.info("...directory separator check complete\n")
