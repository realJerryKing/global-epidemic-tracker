"""Conservative descriptive pilot bands, never population prevalence or a diagnosis."""
from collections import Counter, defaultdict
from datetime import timedelta

from .regions import REGIONS, ancestry


def eligible(group):
    positives = sum(x[0] for x in group.values())
    return len(group) >= 30 and min(positives, len(group) - positives) >= 5


def geographically_mixed(group):
    counts = Counter(value[1] for value in group.values())
    return len(counts) >= 3 and max(counts.values()) <= len(group)*0.6


def summarize(code, groups):
    current = groups[0]
    n = len(current)
    low = min(90, (100 * sum(x[0] for x in current.values()) // n // 10) * 10)
    result = dict(sample_band='30-59' if n < 60 else '60-119' if n < 120 else '120+',
                  new_share_band=f'{low}-{100 if low==90 else low+9}%', trend='insufficient_baseline')
    cohort = set(current).intersection(*groups[1:])
    # Require consistent participants and baseline cell floors in all four periods.
    matched = [{k: g[k] for k in cohort} for g in groups]
    if len(cohort) < 0.6*n or not all(eligible(g) for g in matched):
        return result
    if code == '000000' and not all(geographically_mixed(g) for g in matched):
        return result
    numerators = [sum(x[0] for x in g.values()) for g in matched]
    # Same denominator each week: compare integer counts at the 10-point boundary.
    increase = numerators[0] - max(numerators[1:])
    result['trend'] = 'possible_rise' if 10*increase >= len(cohort) else 'no_clear_rise'
    return result


def release(target, rows):
    periods = [(target - timedelta(weeks=i)).isoformat() for i in range(4)]
    groups = defaultdict(lambda: defaultdict(dict))
    for week, member, region, symptom in rows:
        for ancestor in ancestry(region):
            groups[ancestor][week][member] = (symptom == 'new', region[:2])
    valid = {code for code, weeks in groups.items() if eligible(weeks[periods[0]])
             and (code != '000000' or geographically_mixed(weeks[periods[0]]))}
    output = {}
    children = defaultdict(list)
    for code, rec in REGIONS.items():
        children[rec['parent_code']].append(code)

    def visit(code):
        if code in valid:
            output[code] = summarize(code, [groups[code][p] for p in periods])
            residual = groups[code][periods[0]].copy()
            for child in children[code]:
                if child in valid:
                    for member in groups[child][periods[0]]:
                        residual.pop(member, None)
            # If parent-minus-children would isolate a small residual, stop at parent.
            if residual and not eligible(residual):
                return
        for child in children[code]:
            if code in valid and child not in valid:
                continue
            visit(child)
    visit('000000')
    return output
