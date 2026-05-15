import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from processor import MdImageProcessor

test_input = os.path.join(os.path.dirname(__file__), 'test_input')
test_output_struct = os.path.join(os.path.dirname(__file__), 'test_output_struct')
test_output_flat = os.path.join(os.path.dirname(__file__), 'test_output_flat')

def setup_test_data():
    for d in [test_input, test_output_struct, test_output_flat]:
        if os.path.exists(d):
            for root, dirs, files in os.walk(d, topdown=False):
                for f in files:
                    os.remove(os.path.join(root, f))
                for subd in dirs:
                    os.rmdir(os.path.join(root, subd))
            os.rmdir(d)
        os.makedirs(d, exist_ok=True)

    os.makedirs(os.path.join(test_input, 'images'), exist_ok=True)
    os.makedirs(os.path.join(test_input, 'subdir'), exist_ok=True)

    with open(os.path.join(test_input, 'images', 'logo.png'), 'w') as f:
        f.write('fake png content')
    with open(os.path.join(test_input, 'images', 'banner.jpg'), 'w') as f:
        f.write('fake jpg content')
    with open(os.path.join(test_input, 'subdir', 'local.png'), 'w') as f:
        f.write('fake local png')

    with open(os.path.join(test_input, 'hello.md'), 'w', encoding='utf-8') as f:
        f.write('# Hello\n\n![logo](images/logo.png)\n\nSome text\n\n![banner](images/banner.jpg "title")\n')

    with open(os.path.join(test_input, 'subdir', 'readme.md'), 'w', encoding='utf-8') as f:
        f.write('# Readme\n\n![local](local.png)\n\nAlso ref: ![logo](../images/logo.png)\n')

    with open(os.path.join(test_input, 'noimg.md'), 'w', encoding='utf-8') as f:
        f.write('# No images\n\nJust text.\n')

    print('Test data created')
    for root, dirs, files in os.walk(test_input):
        for f in files:
            print(' ', os.path.relpath(os.path.join(root, f), test_input))


def test_keep_structure():
    print('\n=== Test: Keep Structure ===')
    processor = MdImageProcessor(test_input, test_output_struct, keep_structure=True)
    stats = processor.run(callback=lambda level, msg: print(f'  [{level}] {msg}'))
    print(f'Stats: {stats}')
    print('\nOutput files:')
    for root, dirs, files in os.walk(test_output_struct):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), test_output_struct)
            print(f'  {rel}')
    print('\nContent of output/hello.md:')
    with open(os.path.join(test_output_struct, 'hello.md'), 'r', encoding='utf-8') as f:
        print(f.read())
    print('Content of output/subdir/readme.md:')
    with open(os.path.join(test_output_struct, 'subdir', 'readme.md'), 'r', encoding='utf-8') as f:
        print(f.read())


def test_flatten():
    print('\n=== Test: Flatten ===')
    processor = MdImageProcessor(test_input, test_output_flat, keep_structure=False)
    stats = processor.run(callback=lambda level, msg: print(f'  [{level}] {msg}'))
    print(f'Stats: {stats}')
    print('\nOutput files:')
    for root, dirs, files in os.walk(test_output_flat):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), test_output_flat)
            print(f'  {rel}')
    print('\nContent of output/hello.md:')
    with open(os.path.join(test_output_flat, 'hello.md'), 'r', encoding='utf-8') as f:
        print(f.read())
    print('Content of output/subdir_readme.md:')
    with open(os.path.join(test_output_flat, 'subdir_readme.md'), 'r', encoding='utf-8') as f:
        print(f.read())


def test_edge_cases():
    import shutil
    test_edge_in = os.path.join(os.path.dirname(__file__), 'test_edge_in')
    test_edge_out = os.path.join(os.path.dirname(__file__), 'test_edge_out')

    for d in [test_edge_in, test_edge_out]:
        if os.path.exists(d):
            shutil.rmtree(d)

    os.makedirs(test_edge_in, exist_ok=True)
    os.makedirs(os.path.join(test_edge_in, 'pics'), exist_ok=True)

    for name in ['photo.png', 'img.jpg']:
        with open(os.path.join(test_edge_in, 'pics', name), 'w') as f:
            f.write('fake ' + name)

    content = (
        '# Demo\n\n'
        '![photo](pics/photo.png)\n\n'
        '<img src="pics/img.jpg" alt="img" width="200">\n\n'
        'Same name: ![](pics/photo.png)\n'
    )
    with open(os.path.join(test_edge_in, 'demo.md'), 'w', encoding='utf-8') as f:
        f.write(content)

    print('\n=== Test: Edge Cases (HTML img + duplicate names) ===')
    processor = MdImageProcessor(test_edge_in, test_edge_out, keep_structure=True)
    stats = processor.run(callback=lambda l, m: print(f'  [{l}] {m}'))
    print(f'Stats: {stats}')

    print('\nOutput files:')
    for root, dirs, files in os.walk(test_edge_out):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), test_edge_out)
            print(f'  {rel}')

    print('\nContent of output demo.md:')
    with open(os.path.join(test_edge_out, 'demo.md'), 'r', encoding='utf-8') as f:
        print(f.read())

    for d in [test_edge_in, test_edge_out]:
        if os.path.exists(d):
            shutil.rmtree(d)


if __name__ == '__main__':
    setup_test_data()
    test_keep_structure()
    test_flatten()
    test_edge_cases()
    print('\n=== ALL TESTS PASSED ===')
