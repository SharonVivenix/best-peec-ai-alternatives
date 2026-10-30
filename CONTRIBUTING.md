# Contributing

The solver is only as good as the plan facts in `tools.yaml`. The most useful contribution is a corrected price, prompt cap or engine list with a link to the vendor page that shows it.

## Change the data, then regenerate

1. Edit [tools.yaml](tools.yaml). List every self serve plan of a tool, cheapest first.
2. Put each engine in the right bucket:
   * `included` when every subscriber gets it
   * `pool` plus `choose` when the buyer picks a fixed number from a list
   * `addon` when it costs extra, with `addon_price` if the price is public and `null` if it is not
   * the tool level `enterprise` list when only a sales contract includes it
3. Use only the engine ids listed by `python solve.py --list-engines`. Add a new id to `ENGINES` in `solve.py` first if an engine is missing.
4. Update `checked` with the source and the date you looked.
5. Run `python render_table.py --write`, then `python -m unittest discover -s tests`.
6. Open a pull request with the vendor link.

## Accepted

* Price, prompt, engine or plan changes with a source link.
* A new tool, if its pricing page lists engines per plan.
* Better solver logic, with a test that pins the case it fixes.

## Not accepted

* Affiliate or tracking links.
* Review scores and star ratings.
* Currency conversions. Keep the currency the vendor publishes.

## Code

Standard library plus PyYAML, Python 3.9 or newer. Keep each script runnable on its own and keep tests free of network calls.

```bash
pip install -r requirements.txt
python render_table.py --check
python -m unittest discover -s tests -v
```
