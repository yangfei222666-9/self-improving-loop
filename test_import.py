import sys
sys.path.insert(0, '.')

try:
    from self_improving_loop import SelfImprovingLoop
    print('OK: SelfImprovingLoop loaded')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
