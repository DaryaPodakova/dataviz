# -*- coding: utf-8 -*-
"""
«Одним январём» — A4-постер: семь лет кинопроката России,
неделя за неделей.

Одна страница, один график, чистый matplotlib (без seaborn
и внешних стилей). Двухмерное цветовое кодирование:
  - оттенок клетки = страна производства фильма №1 уик-энда
    (красный — Россия, синий — США, серый — другие страны);
  - насыщенность/светлота = сборы всех фильмов чарта за уик-энд
    (млрд руб.) — три рампы выровнены по одной лестнице светлоты
    OKLCH, так что одинаковый бин читается одинаково тёмным;
  - боковая панель = доля уик-эндов года, где №1 — российский
    фильм.

Данные: понедельные чарты Кинопоиска
(kinopoisk_box_office_rus.csv) + карточки фильмов
(kinopoisk_films.csv) из этой же папки.
Выход: a4_week_heatmap.png (300 dpi) и a4_week_heatmap.pdf
(A4 landscape).
"""
import os

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------- палитра -------------------------
# Рампы построены в OKLCH: L = [.93 .86 .78 .69 .60 .51 .42],
# hue 27° (красный) / 258° (синий) / 250° при C=0.014 (серый).
PAPER = "#fafaf7"
INK, INK2, MUTED = "#171614", "#56534d", "#8b8880"
GRID = "#e5e4e0"
RAMPS = {
    "ru": ["#ffdbd4", "#ffbfb7", "#eda198", "#d48178",
           "#ba645b", "#9c4942", "#7a342e"],
    "us": ["#d2eaff", "#b3d3ff", "#93b9f2", "#729ddb",
           "#5581c2", "#3b66a5", "#284d83"],
    "other": ["#e1e9f1", "#cad2da", "#b1b8c0", "#959ca4",
              "#7a8188", "#60676e", "#474e55"],
}
BOUNDS = [0, 0.15, 0.3, 0.5, 0.8, 1.2, 2, 5]  # млрд руб. за уик-энд
ACCENT = RAMPS["ru"][4]

plt.rcParams.update({
    "font.family": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": PAPER,
    "text.color": INK,
    "svg.fonttype": "none",
})

# ---------------------------- данные ----------------------------
bo = pd.read_csv(os.path.join(HERE, "kinopoisk_box_office_rus.csv"),
                 parse_dates=["weekend_date"])
films = pd.read_csv(os.path.join(HERE, "kinopoisk_films.csv"))
films["country"] = films["country"].fillna("")


def bloc(country: str) -> str:
    if ("Россия" in country) or ("СССР" in country):
        return "ru"
    return "us" if "США" in country else "other"


films["bloc"] = films["country"].apply(bloc)
cards = films.drop_duplicates("film_id")[["film_id", "bloc"]]
m = bo.merge(cards, on="film_id", how="left")
m["bloc"] = m["bloc"].fillna("other")

iso = m["weekend_date"].dt.isocalendar()
m["iy"], m["iw"] = iso["year"].astype(int), iso["week"].astype(int)

wk = (m.groupby(["iy", "iw"])
      .agg(gross=("weekend_gross_rub", "sum"),
           date=("weekend_date", "first"))
      .reset_index())
top_idx = m.groupby(["iy", "iw"])["weekend_gross_rub"].idxmax()
lead = m.loc[top_idx, ["iy", "iw", "title_ru", "bloc"]]
wk = wk.merge(lead, on=["iy", "iw"])
wk = wk[wk["iy"].between(2019, 2026)]
wk["g_bln"] = wk["gross"] / 1e9

YEARS = list(range(2019, 2027))
ROW = {y: i for i, y in enumerate(YEARS)}
share_ru = (wk.assign(is_ru=wk["bloc"].eq("ru"))
              .groupby("iy")["is_ru"].agg(["sum", "size"]))
share_ru["pct"] = share_ru["sum"] / share_ru["size"] * 100

# годовые билеты и зрители (полные годы, календарный год уик-энда)
yearly = (m.groupby(m["weekend_date"].dt.year)
           .agg(gross=("weekend_gross_rub", "sum"),
                adm=("weekend_admissions", "sum")))
yearly["price"] = yearly["gross"] / yearly["adm"]
yearly = yearly.loc[2019:2025]  # 2026 неполный — в мини-графики не идёт

# консольная сводка — «исследовательская» часть
print("Уик-эндов с российским фильмом-лидером:")
for y in YEARS:
    s = share_ru.loc[y]
    print(f"  {y}: {int(s['sum']):>2} из {int(s['size'])}"
          f" ({s['pct']:.0f}%)")

# ---------------------- фигура A4 landscape ----------------------
fig = plt.figure(figsize=(11.69, 8.27))

kick = "КИНОПРОКАТ РОССИИ · 2019–2026 · ПОНЕДЕЛЬНЫЕ ЧАРТЫ КИНОПОИСКА"
fig.text(0.055, 0.952, " ".join(kick), fontsize=8.5, color=MUTED)
fig.text(0.055, 0.895, "Семь лет: восхождение российского кино",
         fontsize=24, fontweight="bold")
fig.text(0.055, 0.852,
         "Цвет клетки — страна производства фильма №1 уик-энда: "
         "красный — Россия, синий — США, серый — другие. Чем "
         "насыщеннее, тем больше касса.\nРынок пришёл к российскому "
         "кино, но восстановление кассы во многом обеспечил "
         "подорожавший на 66 % билет: зрителей на 57 % меньше, "
         "чем в 2019-м.",
         fontsize=10.5, color=INK2, va="top", linespacing=1.45)

ax = fig.add_axes([0.055, 0.235, 0.775, 0.545])
sx = fig.add_axes([0.868, 0.235, 0.118, 0.545])
for a in (ax, sx):
    a.set_facecolor(PAPER)
    for sp in a.spines.values():
        sp.set_visible(False)

norm = BoundaryNorm(BOUNDS, 7)

# --------------------------- клетки ---------------------------
GAP, CS = 0.12, 0.88
for _, r in wk.iterrows():
    x = r["iw"] - 1 + GAP / 2
    y = ROW[r["iy"]] + GAP / 2
    k = int(norm(r["g_bln"]))
    ax.add_patch(Rectangle((x, y), CS, CS,
                           facecolor=RAMPS[r["bloc"]][k],
                           edgecolor="none"))

ax.set_xlim(-0.2, 53.4)
ax.set_ylim(9.35, -1.25)
ax.set_xticks([])
ax.set_yticks([ROW[y] + 0.5 for y in YEARS])
ax.set_yticklabels(YEARS, fontsize=9.5, color=INK2)
ax.tick_params(length=0, pad=6)

MONTHS = ["янв", "фев", "мар", "апр", "май", "июн",
          "июл", "авг", "сен", "окт", "ноя", "дек"]
for i, mo in enumerate(MONTHS):
    ax.text(i * 4.345 + 0.1, -0.32, mo, fontsize=8.5, color=MUTED)

# --------------------------- аннотации ---------------------------
ax.text(22.5, ROW[2020] + 0.62, "залы закрыты · апрель–июль 2020",
        fontsize=8.5, color=MUTED, ha="center")
ax.annotate("на конец периода №1 проката — американский «Майкл»",
            xy=(26.5, ROW[2026] + 0.97), xytext=(22.7, 8.95),
            fontsize=9, color=INK2,
            arrowprops=dict(arrowstyle="-", color=INK2, lw=0.9,
                            connectionstyle="arc3,rad=0.2"))

# --------- боковая панель: % уик-эндов с российским №1 ---------
sx.set_xlim(0, 118)
sx.set_ylim(9.35, -1.25)
sx.set_xticks([])
sx.set_yticks([])
sx.text(0, -0.96, "уик-эндов года, где №1 —", fontsize=8, color=MUTED)
sx.text(0, -0.32, "российский фильм", fontsize=8, color=MUTED)
for y in YEARS:
    v = share_ru.loc[y, "pct"]
    sx.add_patch(Rectangle((0, ROW[y] + 0.22), v, 0.56,
                           facecolor=ACCENT, edgecolor="none"))
    bold = "bold" if y in (2019, 2025) else "normal"
    sx.text(v + 3, ROW[y] + 0.5, f"{v:.0f}%", fontsize=8.5,
            color=INK2, va="center", fontweight=bold)
sx.plot([0, 0], [0.1, 7.94], color=GRID, lw=0.8, clip_on=False)
sx.text(0, 8.6, "* 2026 — по 3 июля", fontsize=7.5, color=MUTED)

# --------- легенда: три рампы на общей шкале сборов ---------
counts = wk["bloc"].value_counts()
LABELS = [
    ("ru", f"Россия — №1 в {counts.get('ru', 0)} уик-эндах"),
    ("us", f"США — в {counts.get('us', 0)}"),
    ("other", f"другие страны — в {counts.get('other', 0)}"),
]
lax = fig.add_axes([0.055, 0.058, 0.47, 0.135])
lax.set_facecolor(PAPER)
for sp in lax.spines.values():
    sp.set_visible(False)
lax.set_xticks([])
lax.set_yticks([])
lax.set_xlim(0, 100)
lax.set_ylim(5.3, -1.05)
lax.text(0, -0.45, "чем насыщеннее цвет, тем больше сборы "
         "за уик-энд, млрд ₽", fontsize=8.5, color=INK2)
SW, X0 = 8, 33
for row, (key, label) in enumerate(LABELS):
    lax.text(X0 - 2, row + 0.52, label, fontsize=8.5, color=INK2,
             ha="right", va="center")
    for k, c in enumerate(RAMPS[key]):
        lax.add_patch(Rectangle((X0 + k * SW, row + 0.12),
                                SW - 0.7, 0.8,
                                facecolor=c, edgecolor="none"))
TICKS = ["0", "0,15", "0,3", "0,5", "0,8", "1,2", "2", "5"]
for k, t in enumerate(TICKS):
    lax.text(X0 + k * SW, 3.55, t, fontsize=7.5, color=MUTED,
             ha="center")
lax.add_patch(Rectangle((X0, 4.32), SW - 0.7, 0.8, facecolor=PAPER,
                        edgecolor=GRID, linewidth=0.8))
lax.text(X0 + SW + 1, 4.72, "пустая клетка — нет данных чарта "
         "или залы закрыты (ковид)", fontsize=8, color=INK2,
         va="center")


# --------- мини-графики: билет и зрители, 2019–2025 ---------
def mini(rect, title, values, fmt, unit):
    a = fig.add_axes(rect)
    a.set_facecolor(PAPER)
    for sp in a.spines.values():
        sp.set_visible(False)
    a.set_xticks([])
    a.set_yticks([])
    ys = list(yearly.index)
    a.plot(ys, values, color=INK2, lw=1.8, solid_capstyle="round")
    a.scatter([ys[0], ys[-1]], [values[0], values[-1]], s=22,
              color=[MUTED, ACCENT], zorder=3)
    pad = (max(values) - min(values)) * 0.28
    a.set_ylim(min(values) - pad, max(values) + pad * 2.2)
    a.set_xlim(ys[0] - 0.4, ys[-1] + 0.4)
    a.text(ys[0], values[0] + pad * 0.7, fmt(values[0]),
           fontsize=8.5, color=INK2, ha="left")
    a.text(ys[-1], values[-1] + pad * 0.7, fmt(values[-1]),
           fontsize=9, color=INK, ha="right", fontweight="bold")
    a.text(ys[0], min(values) - pad * 0.9, str(ys[0]),
           fontsize=7.5, color=MUTED, ha="center", va="top")
    a.text(ys[-1], min(values) - pad * 0.9, str(ys[-1]),
           fontsize=7.5, color=MUTED, ha="center", va="top")
    delta = values[-1] / values[0] - 1
    dtxt = f"{delta:+.0%}".replace("%", " %").replace("-", "−")
    a.set_title(f"{title}, {unit} · {dtxt}",
                fontsize=8.5, color=INK2, loc="left", pad=4)


mini([0.585, 0.085, 0.155, 0.075], "Средний билет",
     list(yearly["price"]), lambda v: f"{v:.0f}", "₽")
mini([0.815, 0.085, 0.155, 0.075], "Зрителей за год",
     [v / 1e6 for v in yearly["adm"]],
     lambda v: f"{v:.0f}".replace(".", ","), "млн")

credit = fig.text(0.986, 0.952,
                  "данные: Кинопоиск · канал «Сделай это красиво» — "
                  "t.me/perfectgraphs/361",
                  fontsize=8, color=MUTED, ha="right")
credit.set_url("https://t.me/perfectgraphs/361")

OUT = "heatmap_rise_of_russian_cinema"
fig.savefig(os.path.join(HERE, OUT + ".png"), dpi=300)
fig.savefig(os.path.join(HERE, OUT + ".pdf"))
print(f"Сохранено: {OUT}.png (300 dpi), {OUT}.pdf (A4 landscape)")
