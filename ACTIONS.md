# La stratégie du bot sur les actions américaines

Calculé le 2026-11-15 avec les prix de Yahoo Finance (dividendes inclus). Frais de 0,1 % par transaction, stop-loss de 8 %. Les montants sont en dollars américains ; le taux de change n'est pas compté. L'argent qui attend en dollars ne rapporte aucun intérêt dans ce test.

- **Hausse seulement** : le bot achète le FNB de l'indice quand la moyenne courte passe au-dessus de la longue, et reste en dollars sinon.
- **Hausse et baisse** : quand la moyenne courte passe sous la longue, il achète en plus le FNB inversé (SH pour le S&P 500, PSQ pour le Nasdaq).

## S&P 500 (SPY, inversé : SH)

Période : du 2023-09-01 au 2026-11-13 (0,2 ans).

| Stratégie | Rendement total | Par an | Chute max | Transactions (gagnantes) | Temps investi |
|---|---|---|---|---|---|
| Acheter et garder | +72 % | +2976,4 % | 8 % | 0 (0) | 100 % |
| Bot hausse seulement (10/30) | +51 % | +1248,8 % | 8 % | 1 (0) | 90 % |
| Bot hausse et baisse (10/30) | +51 % | +1248,8 % | 8 % | 1 (0) | 90 % |
| Bot hausse seulement (50/200) | +51 % | +1248,8 % | 8 % | 1 (0) | 90 % |
| Bot hausse et baisse (50/200) | +51 % | +1248,8 % | 8 % | 1 (0) | 90 % |

**Sur 9 réglages de moyennes** (rendement par an, du pire au meilleur, et réglages qui battent « garder ») :

| Stratégie | Pire | Médian | Meilleur | Battent « garder » | Chute max médiane |
|---|---|---|---|---|---|
| Bot hausse seulement | +1248,8 % | +1248,8 % | +1248,8 % | 0/9 | 8 % |
| Bot hausse et baisse | +1248,8 % | +1248,8 % | +1248,8 % | 0/9 | 8 % |

**Pendant les grandes baisses** (réglage classique 50/200) :

| Période | Acheter et garder | Bot hausse seulement | Bot hausse et baisse |
|---|---|---|---|

**Avec un petit compte** (commission de 1 $ US sur 200 $, soit 0,5 % par ordre, réglage 10/30) :

| Stratégie | Par an avec 1 000 $ | Par an avec 200 $ |
|---|---|---|
| Bot hausse seulement | +1248,8 % | +1119,5 % |
| Bot hausse et baisse | +1248,8 % | +1119,5 % |

## Nasdaq 100 (QQQ, inversé : PSQ)

Période : du 2023-09-01 au 2026-11-13 (0,2 ans).

| Stratégie | Rendement total | Par an | Chute max | Transactions (gagnantes) | Temps investi |
|---|---|---|---|---|---|
| Acheter et garder | +81 % | +4162,2 % | 10 % | 0 (0) | 100 % |
| Bot hausse seulement (10/30) | +96 % | +6875,2 % | 10 % | 0 (0) | 93 % |
| Bot hausse et baisse (10/30) | +111 % | +10815,8 % | 10 % | 1 (1) | 98 % |
| Bot hausse seulement (50/200) | +56 % | +1525,2 % | 10 % | 1 (0) | 90 % |
| Bot hausse et baisse (50/200) | +56 % | +1525,2 % | 10 % | 1 (0) | 90 % |

**Sur 9 réglages de moyennes** (rendement par an, du pire au meilleur, et réglages qui battent « garder ») :

| Stratégie | Pire | Médian | Meilleur | Battent « garder » | Chute max médiane |
|---|---|---|---|---|---|
| Bot hausse seulement | +1525,2 % | +1525,2 % | +6875,2 % | 1/9 | 10 % |
| Bot hausse et baisse | +1525,2 % | +1525,2 % | +10815,8 % | 1/9 | 10 % |

**Pendant les grandes baisses** (réglage classique 50/200) :

| Période | Acheter et garder | Bot hausse seulement | Bot hausse et baisse |
|---|---|---|---|

**Avec un petit compte** (commission de 1 $ US sur 200 $, soit 0,5 % par ordre, réglage 10/30) :

| Stratégie | Par an avec 1 000 $ | Par an avec 200 $ |
|---|---|---|
| Bot hausse seulement | +6875,2 % | +6532,3 % |
| Bot hausse et baisse | +10815,8 % | +9769,1 % |

Un bon résultat passé ne garantit rien pour la suite. Ce n'est pas un conseil financier.
