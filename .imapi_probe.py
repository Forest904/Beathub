import sys
import comtypes.client as cc
try:
    tlb = cc.GetModule(('imapi2.tlb'))
    print('Loaded imapi2.tlb')
except Exception as e:
    print('GetModule imapi2.tlb failed:', e)
try:
    obj = cc.CreateObject('IMAPI2.MsftDiscMaster2')
    print('Created MsftDiscMaster2 COM object:', obj)
    import comtypes.gen
    print('comtypes.gen packages:', [n for n in dir(comtypes.gen) if n.upper().startswith('IMAPI')])
    mod = None
    for name in dir(comtypes.gen):
        m = getattr(comtypes.gen, name)
        if hasattr(m, 'IDiscFormat2AudioCD'):
            mod = m
            print('Found module by symbol:', name)
            break
    if mod:
        print('Has IDiscFormat2AudioCD?', hasattr(mod, 'IDiscFormat2AudioCD'))
        print('Has MsftDiscFormat2AudioCD?', hasattr(mod, 'MsftDiscFormat2AudioCD'))
        print('Has IDiscFormat2Data?', hasattr(mod, 'IDiscFormat2Data'))
        IDiscFormat2AudioCD = getattr(mod, 'IDiscFormat2AudioCD', None)
        if IDiscFormat2AudioCD:
            names = [n for n in dir(IDiscFormat2AudioCD) if any(n.startswith(p) for p in ('Add', 'put_', 'get_', 'Set', 'Write'))]
            print('IDiscFormat2AudioCD selected methods sample:', names[:40])
except Exception as e:
    print('Error creating/introspecting IMAPI2:', e)
