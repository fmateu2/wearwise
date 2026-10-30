"""Run the original WearWise engine on illustrative data, without external services."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from forward_chaining import recommend_outfit_forward_chaining


def main():
    rules = json.loads((ROOT / 'normalization.json').read_text())
    garments = json.loads((ROOT / 'examples/wardrobe.json').read_text())
    contexts = [
        dict(temperature=0, season='winter', formality='business_casual', occasion='work'),
        dict(temperature=18, season='spring', formality='business_casual', occasion='work'),
        dict(temperature=28, season='summer', formality='casual', occasion='travel'),
    ]
    for context in contexts:
        outfit = recommend_outfit_forward_chaining(context, garments, rules)
        print(
            json.dumps(
                {
                    'context': context,
                    'outfit': {
                        key: (
                            [g['name'] for g in value]
                            if isinstance(value, list)
                            else value['name'] if value else None
                        )
                        for key, value in outfit.items()
                    },
                },
                indent=2,
            )
        )


if __name__ == '__main__':
    main()
