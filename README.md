# IPK - 1. projekt

Server komunikující pomocí HTTP protokolu, který podporuje dvě základní medoty, pomocí nichž lze získat přreklad doménového jména na IP adresu a naopak.

## Metoda GET
formát požadavku:
  - GET /resolve?name=\[NAME]&type=\[TYPE] HTTP/1.1

formát odpovědi:
  - \[NAME]:\[TYPE]=\[RESPONSE]

parametry:
  - NAME = IP adresa, případně doménové jméno určené k přeložení
  - TYPE = Určení typu překladu, nabývá dvou hodnot:
    - A - jménem musí být doména, v opačném případě se jedná o chybový stav. Vrací překlad doménového jména na IP adresu.
    - PTR - jménem je IP adresa, jinak dotaz končí chybou. Vrací překlad IP adresy na doménové jméno.
  - RESPONSE = překlad daného jména NAME dle typu TYPE

## METODA POST
Součástí požadavku je seznam dotazů, z nichž každý je na samostatném řádku.

formát požadavku:
  - POST /dns-query HTTP/1.1

formát dotazu:
  - \[NAME]:\[TYPE]

Formát odpovědi je stejný jako u metody GET s tím, že výstupem je opět seznam, kdy na každém řádku je zodpovězen jeden dotaz.
Dotazy, které jsou chybné, nebo je nebylo možné vyřešit se automatickt přeskakují. K chybě dochází pouze, pokud nebyl proveden ani jeden dotaz nebo pokud se na vstupu objeví prázdný řádek. Parametry jssou již také popsány u předchozí metody.
 

## Spuštění
Nejprve si stáhněte daný archiv, rozbalte ho, otevřete složku s projektem v terminálu a spusťte skript příkazem:
```sh
$ make run PORT=8080
```
  - PORT=`8080` - udává číslo portu, na kterém má být server spuštěn, v tomto případě je to `8080` 

## Testování
K testobání slouží příkaz `curl`.

### Test metody GET
příklad platných dotazů(na lokální port `8080`):
```sh
$ curl localhost:8080/resolve?name=www.fit.vutbr.cz\&type=A
```
```sh
$ curl localhost:8080/resolve?name=147.229.14.131\&type=PTR
```
odpovědi:
  - www.fit.vutbr.cz:A=147.229.9.23
  - 147.229.14.131:PTR=dhcpz131.fit.vutbr.cz

### Test metody POST
modelový dotaz(opět na lokální port `8080`):
```sh
$ curl --data-binary @queries.txt -X POST http://localhost:8080/dns-query
```
Soubor `queries.txt` obsahuje na každém řádku jeden dotaz:
  - www.google.com:A
  - www.seznam.cz:A
  - 147.229.14.131:PTR

odpovědi:
  - www.google.com:A=216.58.201.68
  - www.seznam.cz:A=77.75.74.176
  - 147.229.14.131:PTR=dhcpz131.fit.vutbr.cz

## Základní logiga
použité knihovny:
```python
import re
import sys
import socket
```
  - `re` - použita pro zpracování řetězců jednotlivých dotazů
  - `sys` - zpracování vstupního argumentu skriptu (PORT) 
  - `socket` - vytvoření serveru a také řšení překladů

Samotný server je řešen nekonečným cyklem, přičemž čeká na požadavky. Při přijetí požadavku jsou načtena data a je volána funkce `proccessMethod(data, conn)`, která zkontroluje danou přijatou metodu a vrátí chybovou odpověd, pokud je daná metoda nepodporovaná. Podle přijaté metody tato funkce dále volá funkci `doGet(data, conn)`, nebo `doPost(data,conn)`. Tyto funkce slouží k obsoužení daného požadavku. Probíhá v nich kontrola formátu, případně parametrů přijatých dotazů a také vytvoření těla odpovědi. Samotná odpověď je poté odesílána funkcí `sendResponse(conn, code, body, data)`. Zde dochází k vytvoření patřičné hlavičky dané odpovědi, vybrání správného kódu, hlášení a nakonec k odeslání celé této zprávy.