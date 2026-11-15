# La stratégie du bot sur les actions américaines

Calculé le 2026-11-15 avec les prix de Yahoo Finance (dividendes inclus). Frais de 0,1 % par transaction, stop-loss de 8 %. Les montants sont en dollars américains ; le taux de change n'est pas compté. L'argent qui attend en dollars ne rapporte aucun intérêt dans ce test.

- **Hausse seulement** : le bot achète le FNB de l'indice quand la moyenne courte passe au-dessus de la longue, et reste en dollars sinon.
- **Hausse et baisse** : quand la moyenne courte passe sous la longue, il achète en plus le FNB inversé (SH pour le S&P 500, PSQ pour le Nasdaq).

## S&P 500 (SPY, inversé : SH)

Période : du 2007-10-18 au 2026-11-13 (19,0 ans).

| Stratégie | Rendement total | Par an | Chute max | Transactions (gagnantes) | Temps investi |
|---|---|---|---|---|---|
| Acheter et garder | +594 % | +10,7 % | 55 % | 0 (0) | 100 % |
| Bot hausse seulement (10/30) | +142 % | +4,7 % | 21 % | 72 (32) | 64 % |
| Bot hausse et baisse (10/30) | −41 % | −2,7 % | 69 % | 140 (46) | 92 % |
| Bot hausse seulement (50/200) | +310 % | +7,7 % | 32 % | 12 (6) | 77 % |
| Bot hausse et baisse (50/200) | +93 % | +3,5 % | 47 % | 28 (8) | 98 % |

**Sur 9 réglages de moyennes** (rendement par an, du pire au meilleur, et réglages qui battent « garder ») :

| Stratégie | Pire | Médian | Meilleur | Battent « garder » | Chute max médiane |
|---|---|---|---|---|---|
| Bot hausse seulement | +4,6 % | +6,8 % | +9,1 % | 0/9 | 23 % |
| Bot hausse et baisse | −2,7 % | +1,0 % | +5,0 % | 0/9 | 53 % |

**Pendant les grandes baisses** (réglage classique 50/200) :

| Période | Acheter et garder | Bot hausse seulement | Bot hausse et baisse |
|---|---|---|---|
| Krach COVID 2020 | −34 % | −31 % | −31 % |
| Baisse de 2022 | −24 % | −9 % | +10 % |

**Avec un petit compte** (commission de 1 $ US sur 200 $, soit 0,5 % par ordre, réglage 10/30) :

| Stratégie | Par an avec 1 000 $ | Par an avec 200 $ |
|---|---|---|
| Bot hausse seulement | +4,7 % | +1,6 % |
| Bot hausse et baisse | −2,7 % | −8,3 % |

## Nasdaq 100 (QQQ, inversé : PSQ)

Période : du 2007-10-18 au 2026-11-13 (19,0 ans).

| Stratégie | Rendement total | Par an | Chute max | Transactions (gagnantes) | Temps investi |
|---|---|---|---|---|---|
| Acheter et garder | +1384 % | +15,2 % | 53 % | 0 (0) | 100 % |
| Bot hausse seulement (10/30) | +350 % | +8,2 % | 30 % | 72 (37) | 64 % |
| Bot hausse et baisse (10/30) | −28 % | −1,7 % | 62 % | 140 (49) | 93 % |
| Bot hausse seulement (50/200) | +837 % | +12,5 % | 29 % | 14 (9) | 79 % |
| Bot hausse et baisse (50/200) | +294 % | +7,5 % | 39 % | 35 (12) | 97 % |

**Sur 9 réglages de moyennes** (rendement par an, du pire au meilleur, et réglages qui battent « garder ») :

| Stratégie | Pire | Médian | Meilleur | Battent « garder » | Chute max médiane |
|---|---|---|---|---|---|
| Bot hausse seulement | +6,4 % | +9,1 % | +12,5 % | 0/9 | 30 % |
| Bot hausse et baisse | −4,3 % | +2,3 % | +7,5 % | 0/9 | 49 % |

**Pendant les grandes baisses** (réglage classique 50/200) :

| Période | Acheter et garder | Bot hausse seulement | Bot hausse et baisse |
|---|---|---|---|
| Krach COVID 2020 | −28 % | −29 % | −29 % |
| Baisse de 2022 | −34 % | −13 % | +6 % |

**Avec un petit compte** (commission de 1 $ US sur 200 $, soit 0,5 % par ordre, réglage 10/30) :

| Stratégie | Par an avec 1 000 $ | Par an avec 200 $ |
|---|---|---|
| Bot hausse seulement | +8,2 % | +5,0 % |
| Bot hausse et baisse | −1,7 % | −7,4 % |

Un bon résultat passé ne garantit rien pour la suite. Ce n'est pas un conseil financier.
