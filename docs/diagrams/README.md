# Diagrams

The diagrams in this project are authored as self-contained HTML/CSS pages in [`src/`](src) and
rendered to high-resolution PNGs with headless Chromium. Authoring them as code keeps them in
version control and reproducible, and rendering to PNG means they display reliably on GitHub.

## Regenerate

```bash
pip install playwright
playwright install chromium
python docs/diagrams/render.py                 # render every src/*.html
python docs/diagrams/render.py 01-architecture # render one
```

Each source is a 1440x1040 page; the renderer captures it at 2x. Edit the HTML in `src/`, re-run
the renderer, and commit the updated PNG.

## The set

| File | Shows |
| --- | --- |
| `01-architecture.png` | The three guarantees qedra makes |
| `02-neuro-symbolic.png` | The neural / symbolic boundary |
| `03-reference-architecture.png` | The three-tier reference workload and its verdicts |
| `04-cicd-gate.png` | qedra as a pull-request merge gate |
