import argparse
import pathlib
import pandas as pd
import numpy as np

from dataclasses import dataclass
from typing import List
from loin.en_17412_3 import (
    LevelOfInformationNeed,
    Specification,
    SpecificationPerObjectType,
    ObjectType,
)
from loin.iso_23887 import (
    DataTemplateType,
    DatatypeType,
    DatatypeTypeName,
    MultilingualTextType,
    ScaleType,
    PropertyType,
    ReferenceType,
    UnitType,
    BaseType,
)
from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.models.datatype import XmlDateTime


# Define a container dataclass to hold objects of different types
@dataclass
class Container:
    Loin: List[LevelOfInformationNeed]
    Object: List[ObjectType]
    Unit: List[UnitType]
    Property: List[PropertyType]


def default_loader(xls_file: pathlib.Path, *, obj_cols: int = 3,
                   header_rows: int = 2, lang: str = "en") -> Container:
    data = pd.read_excel(xls_file, skiprows=1)
    date = XmlDateTime.now()

    loin = LevelOfInformationNeed()

    phases = [int(i) for i in set(data.iloc[1, obj_cols:])]
    num_phases = len(phases)

    def phase_from_idx(idx):
        return ((idx - obj_cols - 1) % num_phases) + 2

    property_names = list(data.columns[obj_cols::num_phases])

    objects: List[ObjectType] = []
    properties: List[PropertyType] = []

    def property_name_from_idx(idx):
        return property_names[(idx - obj_cols) // num_phases]

    for phase in phases:
        specification = Specification()
        # TODO: add actors and all this in the Prerequisites
        loin.specification.append(specification)

        specification.description = "Some description"
        specification.name = f"Specification for phase {phase}"

        for row_id in range(header_rows, len(data)):
            row = data.iloc[row_id]

            specification_per_object_type = SpecificationPerObjectType()
            specification.specification_per_object_type.append(
                specification_per_object_type)

            object_type = ObjectType(date=date)
            object_name = "_".join(row.iloc[:obj_cols])
            object_type.name.append(MultilingualTextType(object_name, lang))
            object_type_ref = ReferenceType(node_id=object_type.node_id)
            specification_per_object_type.object_type = object_type
            objects.append(object_type)

            data_template = DataTemplateType(date=date)
            data_template.object_value.append(object_type_ref)

            for col_id in range(obj_cols, len(row)):
                if pd.isna(row.iloc[col_id]):
                    continue
                this_phase = phase_from_idx(col_id)
                if this_phase != phase:
                    continue
                property = PropertyType(date=date)
                property.name.append(MultilingualTextType(
                    property_name_from_idx(col_id), lang))
                property_ref = ReferenceType(node_id=property.node_id)
                properties.append(property)
                data_template.property.append(property_ref)

            specification_per_object_type.alphanumerical_information.append(
                data_template)

    return Container(Loin=[loin], Object=objects, Unit=[], Property=properties)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("--format", type=str, default="default")
    parser.add_argument("--lang", type=str, default="en")
    args = parser.parse_args()

    if args.format == "default":
        loader = default_loader
    else:
        raise NotImplementedError(f"Format {args.type} not implemented")

    serializer_config = SerializerConfig(
        # Enable pretty-printing (adds line breaks and indentation)
        pretty_print=True,
        # Indentation using 4 spaces (adjust as needed)
        pretty_print_indent="    "
    )

    # Serialize the object into an XML instance file
    serializer = XmlSerializer(config=serializer_config)

    container = loader(args.input, lang=args.lang)
    xml_instance = serializer.render(container)

    # Write the XML instance to a file
    with open(args.output, "w") as f:
        f.write(xml_instance)


if __name__ == "__main__":
    main()
