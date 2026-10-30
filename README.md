# WearWise

### Understand the clothes. Explain the outfit.

An academic wardrobe assistant that combines image-based attribute extraction with explicit, context-aware rules. WearWise recommends combinations from an existing wardrobe and separates perception from recommendation logic.

**Python · Streamlit · MongoDB · OpenAI API · Forward chaining**

**Team:** Francesc Mateu Vallespín, Pau Porta Roca, Giovanni Luca Giraldo Cabana and Jan Francesc Porcar.

## What the project does

1. Accepts one or more clothing images in a Streamlit interface.
2. Uses `gpt-4o` to extract garment attributes, then `gpt-4o-mini` for a second correction pass.
3. Maps attributes to controlled vocabulary through eight normalization dictionaries.
4. Stores one document per detected garment in MongoDB, retaining raw, corrected and normalized attributes plus a thumbnail.
5. Converts context into facts and applies explicit rules until no new facts are added.
6. Filters candidates, ranks them and assembles a top, bottom, shoes and available extras.

The aim is to help people use clothing they already own. Environmental impact, recommendation quality and extraction accuracy have not been quantified by the checks in this package.

## Architecture

| Module | Responsibility |
| --- | --- |
| `UserInterface.py` | Streamlit upload flow, context inputs and outfit display |
| `agent.py` | Image extraction, second-pass correction and normalization orchestration |
| `normalizer.py` | Maps extracted terms to controlled attributes |
| `normalization.json` | Eight normalization maps and six rule groups |
| `db.py` | MongoDB connection and garment persistence helpers |
| `forward_chaining.py` | Fact derivation, candidate filtering, scoring and outfit assembly |

The six configured rule groups cover color, temperature, pattern, formality, occasion and category combinations. Their effects differ: some derive facts, some affect ranking, and some are configuration for future extensions rather than active assembly constraints.

The two model calls extract and correct attributes. They do not generate the final outfit. That recommendation is produced by Python rules and heuristic scores.

## Quick start: offline rules demo

The recommendation engine has no external dependencies. Try it with the included, explicitly illustrative wardrobe:

```bash
python scripts/offline_demo.py
```

This runs three contexts without an API key, database or network connection. The sample wardrobe was added for the portfolio; it is not a dump of the original database or an evaluation dataset.

## Run the original Streamlit app

Use Python 3.11 or newer with a virtual environment. The original app requires an OpenAI API key with access to its configured models and a reachable MongoDB instance.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your own credentials and database settings.
streamlit run UserInterface.py
```

On Windows, activate with `.venv\Scripts\activate` and use `copy .env.example .env`. Run from the repository root because the application resolves its rule file relative to the current directory.

Uploading images and clicking **Process Images** sends them to the configured OpenAI service and writes garment records to MongoDB. The local offline demo and browser portfolio demo do neither.

The uploaded `.env`, cached bytecode and operating-system metadata are excluded from this package. Only `.env.example`, containing empty or local example values, is included. Keep real credentials out of source control.

## How recommendations are assembled

**Context facts** include temperature, season, formality and occasion. Temperature is assigned to one of five bands: very cold, cold, mild, warm or hot.

**Fact derivation** adds requested garments, exclusions, allowed types and compatibility facts. The loop stops when the fact set stops changing.

**Filtering** removes candidates that conflict with the implemented season, type or style exclusions. The function named `is_garment_safe` performs these rule checks; its name does not imply a validated physical-safety assessment.

**Scoring** then rewards or penalizes individual candidates:

| Condition | Score change |
| --- | --- |
| Exact occasion match | +10 |
| Occasion mismatch, except outerwear | −5 |
| Exact formality match | +5 |
| Exact material, style or color preference | +5 for each matching preference |
| Color compatible with a context color | +3 per matching garment color |
| Candidate outside the derived allowed-type set | −20, in a separate fallback pool |

Strict candidates are considered before the fallback pool. This is not a single globally optimized ranking. Core slots are selected independently, followed by available requested extras. A complete outfit is not guaranteed when the wardrobe lacks a suitable candidate.

The original Streamlit form provides temperature, season, formality and occasion. Preference and color compatibility code exists in the engine, but the form does not collect all of those optional inputs.

## Portfolio demo

The website includes a JavaScript adaptation of the original Python engine and an illustrative wardrobe. It adds a visible explanation of derived facts, candidate scores, fallbacks and unfilled requests. This explanation panel is a portfolio addition; the original Streamlit UI mainly displays the chosen garments.

The downloadable package includes the original Python logic and an offline demo. The website's JavaScript implementation is maintained in the portfolio repository and checked against this Python engine across a context matrix.

## Verification

```bash
python -m unittest discover -s tests
```

The offline tests cover temperature boundaries, season and style exclusions, fallback behavior and consistent candidate assembly. They verify implemented behavior, not fashion quality, real-world safety, sustainability impact or model accuracy. The paid image-extraction service and original MongoDB connection were not exercised during portfolio packaging.

## Known implementation boundaries

- **Vocabulary alignment:** several rules use terms such as `tank_top`, `dress_pants` and `formal_shoes`, while normalization preserves different specific garment terms. This can leave intended restrictions or requests unmatched.
- **Optional rules:** pattern compatibility facts and `category_matching` configurations are not consumed by the final selector. The occasion rule file uses `forbidden` in one place while the engine reads `forbidden_items`.
- **Fallbacks:** when strict options are unavailable, the engine can choose a lower-ranked candidate from its fallback pool. Formality is therefore not guaranteed in every result.
- **Required items:** requests are filled opportunistically. Outerwear is matched broadly by category and existing footwear can satisfy the slot without matching the requested shoe type. Extras may vary in order because Python iterates a set.
- **Temperature gaps:** integer temperatures are used by the demo. The original inclusive bands leave gaps at fractional values such as 5.5°C.
- **Data robustness:** the app assumes usable extracted JSON and a consistent wardrobe schema. Authentication, per-user database isolation, stronger validation and end-to-end tests remain future work.

These observations refer to the supplied code. The academic report describes some intended behavior more broadly; this README follows the implementation.

## Next iteration

Unify the vocabulary across extraction and rules, validate attributes before storage, make all required-item handling explicit, and expose rule explanations in the original application. Add robust tests and per-user storage before treating it as a multi-user service.

## Credits and provenance

This is a four-person academic project at La Salle — Universitat Ramon Llull. Component-level individual ownership has not been assigned in this package.

Original source and rule behavior are preserved. Packaging adds documentation, `.env.example`, an illustrative sample wardrobe, an offline runner and tests. The original report, presentation and README are retained in `docs/`.

No new open-source licence is assigned by this packaging work. Contact the authors about reuse.

## Public document copy

The report retains its technical content, diagrams and coauthor names. Student contact addresses and private collaboration invitations are omitted from the public copy.

