import sys
sys.path.insert(0, 'backend')
import Levenshtein

submitted = 'netfl1x-billing'
# After leet (1->l): netfllx-billing → split → ['netfllx', 'billing']
components = ['netfllx', 'billing']
known = 'netflix'

for comp in components:
    max_len = max(len(comp), len(known))
    dist = Levenshtein.distance(comp, known)
    sim = 1 - dist / max_len
    print(f'Component "{comp}" vs "{known}": distance={dist}, similarity={sim:.1%}, with penalty={sim*0.94:.1%}')

best = max(
    (1 - Levenshtein.distance(c, known) / max(len(c), len(known))) * 0.94
    for c in components if len(c) >= 3
)
print(f'\nBest component score: {best:.1%}')
print(f'Threshold: 75.0%')
print(f'Will flag as impersonation: {best >= 0.75}')
