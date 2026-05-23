import pathlib

from codegen.civinst_handler import CivInstHandler
from codegen.alignment_handler import AlignmentHandler
from codegen.needs_handler import Needs
from codegen.measures.handler import MeasureHandler

if __name__ == "__main__":
    ciso_common = pathlib.Path(__file__).resolve().parent / "ciso_common"

    CivInstHandler(list((ciso_common / "civil_institutions").glob("*.txt")))
    MeasureHandler(list((ciso_common / "measures").glob("*.txt")))
    Needs(list((ciso_common / "needs").glob("*.txt")))
    AlignmentHandler([ciso_common / "alignments.txt"])
