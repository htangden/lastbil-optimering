# Logistikoptimering

Programmet optimerar antalet lastbilar som bör köra sträckorna från fabrik till grossist. Därutöver bestämmer modellen en plats för ett mellanlager till vilket frakt kan ske med tåg för att minska miljöpåverkan. 

## Användning

Datan med vilken resultatet ska ges skrivs i en .txt-fil enligt följande format:

<pre>
FABRIKER
Älmhult 56.59 14.16 100
[fler liknande rader]

GROSSISTER
Halmstad 56.67 12.86 70
[fler liknande rader]
</pre>

För en fabrik anges först namnet, sedan longitud respektive latitud och slutligen produktionsmängd.
För en grossist anges först namnet, sedan longitud respektive latitud och slutligen behov.

Behov och produktionsmängd anges i enheten "lastbil".

Programmet körs sedan genom att köra `lastbil.py` med path till txt-fil med data som kommandoradsargument. Då datan ligger i filen `data.txt` blir detta

<pre>
python lastbil.py data.txt
</pre>

Resultatet presenteras därefter i mappen `output` i `solution.txt` och även grafiskt i filen `solution.png`. Ifall kartbakgrunden inte önskas anges `False` efter filnamn som kommandoradsarugment.

<pre>
python lastbil.py data.txt False
</pre>


