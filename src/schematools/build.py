#!/usr/bin/env python3
"""Builds the schema.py module."""
import sys
import json


def stripComments(o):  # pylint: disable=too-many-return-statements
    """Traverse the dictionary o and remove any keys named "$comment"."""
    match o:
        case str():
            return o
        case dict():
            iret = {}
            for k, v in o.items():
                if k == "$comment":
                    continue
                iret[k] = stripComments(v)
            return iret
        case list():
            return [stripComments(x) for x in o]
        case int():
            return o
        case float():
            return o
        case None:
            return o
        case _:
            print(o)
            return o


SCHEMA_HEADER = '''
"""Auto-generated schema validators for the JSON used by the main CLI."""
# pylint: disable=line-too-long
import json
from jsonschema import Draft7Validator
from referencing import Registry
from referencing.jsonschema import DRAFT7
from jsonschema import validators
import numpy as np
import matplotlib.colors as mplcolors
# DO NOT EDIT THIS FILE - IT IS AUTO-GENERATED BY build.py
# TO CHANGE A SCHEMA, EDIT THE CORRESPONDING .schema FILE
# AND RUN make schemas OR make all IN THE src DIRECTORY.

def _isColorMap(checker, instance):
    return isinstance(instance, mplcolors.Colormap)

def _isNumpyArray(checker, instance):
    return isinstance(instance, np.ndarray)

def _isArray(checker, instance):
    return isinstance(instance, list) or isinstance(instance, tuple)

_typeChecker = Draft7Validator.TYPE_CHECKER.redefine_many(
    {
        "ndarray": _isNumpyArray,
        "colormap": _isColorMap,
        "array": _isArray
    })

CustomValidator = validators.extend(Draft7Validator,
    type_checker=_typeChecker)

'''


def build():
    """Read in the .schema files and generate schema.py."""
    with open(sys.argv[1], "w") as fp:
        fp.write(SCHEMA_HEADER)
        for schemaFname in sys.argv[2:]:
            fp.write("_" + schemaFname + 'Schema = json.loads("""')
            with open("schematools/" + schemaFname + ".schema", "r") as sfp:
                jsonStr = json.dumps(stripComments(json.load(sfp)))
                fp.write(jsonStr)
            fp.write('""")  # noqa\n')
            fp.write("_" + schemaFname + "Schema['$id'] = 'https://example.com/"
                    "schema/" + schemaFname + "'\n")
        fp.write("_schemaStore = {")
        for schemaFname in sys.argv[2:]:
            fp.write(f"_{schemaFname}Schema['$id']: _{schemaFname}Schema,")
        fp.write("}\n")
        fp.write("_storeList = [(x, DRAFT7.create_resource(_schemaStore[x])) "
                "for x in _schemaStore.keys()]\n")
        fp.write("_registry = Registry().with_resources(_storeList)\n")
        fp.write("\n\n")
        for schemaFname in sys.argv[2:]:
            fp.write(
                f"{schemaFname}: CustomValidator = "
                f"CustomValidator(_{schemaFname}Schema, registry=_registry)\n")
            docName = schemaFname
            fmtStr = '"""Validator for :py:{type:s}:`{name:s}<bpreveal.{module:s}>`' \
                     '\n\n:meta hide-value:\n"""\n'
            if docName in {"base", "prepareBed_old"}:
                continue
            if schemaFname == "pisaGraph":
                mtype = "func"
                mname = "plotPisaGraph"
                mmodule = "plotting.plotPisaGraph"
            elif schemaFname == "pisaPlot":
                mtype = "func"
                mname = "plotPisa"
                mmodule = "plotting.plotPisa"
            elif schemaFname in {"addNoise"}:
                mtype = "mod"
                mname = "addNoise"
                mmodule = "tools.addNoise"
            else:
                mtype = "mod"
                mname = schemaFname
                mmodule = schemaFname
            fp.write(fmtStr.format(type=mtype, name=mname, module=mmodule))
        fp.write("schemaMap = {")
        for schemaFname in sys.argv[2:]:
            fp.write(f'"{schemaFname}": {schemaFname},')
        fp.write("}\n")
        fp.write('"""A mapping from a string naming a BPReveal program to '
            "the corresponding schema.\n\n"
            'Usage::\n\n    schemaMap["prepareBed"](configJson)\n\n:meta hide-value:"""\n')


if __name__ == "__main__":
    build()
# Copyright 2022, 2023, 2024 Charles McAnany. This file is part of BPReveal. BPReveal is free software: You can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 2 of the License, or (at your option) any later version. BPReveal is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details. You should have received a copy of the GNU General Public License along with BPReveal. If not, see <https://www.gnu.org/licenses/>.  # noqa
