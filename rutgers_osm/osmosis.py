def diff(file1, file2, output, format="pbf"):
    return [
        'osmosis',
        '--read-{0}'.format(format),
        'file={0}'.format(file1),
        '--sort',
        '--read-{0}'.format(format),
        'file={0}'.format(file2),
        '--sort',
        '--derive-change',
        '--simplify-change',
        '--sort-change',
        '--write-xml-change',
        'file={0}'.format(output)
    ]

def apply_diff(file1, diff_file, output=None):
    return [
        'osmosis',
        '--read-xml-change',
        'file={0}'.format(diff_file),
        '--sort-change',
        '--read-pbf',
        'file={0}'.format(file1),
        '--sort',
        '--apply-change',
        '--sort',
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
