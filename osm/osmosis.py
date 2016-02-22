def diff(file1, file2, output, bbox=None):
    osmosis_cmd = [
        'osmosis',
        '--read-pbf',
        'file={0}'.format(file1),
        '--read-pbf',
        'file={0}'.format(file2)
    ]

    if bbox is not None:
        osmosis_cmd = osmosis_cmd.extend([
            '--bounding-box',
            'left={0}'.format(bbox[0]),
            'bottom={0}'.format(bbox[1]),
            'right={0}'.format(bbox[2]),
            'top={0}'.format(bbox[3])
        ])

    osmosis_cmd = osmosis_cmd.extend([
        '--derive-change',
        '--simplify-change',
        '--sort',
        '--write-xml-change',
        'file={0}'.format(output)
    ])

    return osmosis_cmd

def apply_diff(file1, diff_file, output=None):
    return [
        'osmosis',
        '--read-pbf',
        'file={0}'.format(file1),
        '--read-xml-change',
        'file={0}'.format(diff_file),
        '--apply-change',
        '--write-pbf',
        'file={0}'.format(output if output is not None else file1)
    ]

def crop(file1, bbox, output):
    return [
        'osmosis',
        '--read-pbf',
        'file={0}'.format(file1),
        '--bounding-box',
        'left={0}'.format(bbox[0]),
        'bottom={0}'.format(bbox[1]),
        'right={0}'.format(bbox[2]),
        'top={0}'.format(bbox[3]),
        '--sort',
        '--write-xml',
        'file={0}'.format(output)
    ]
