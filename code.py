# Kod nize vznikl upravou oficialni ukazky z GitHubu pro revizi D desky Maker Badge:
# https://github.com/makerfaireczech/maker_badge/blob/main/SW/CircuitPython/examples/MF%20basic%20rev.D/code.py

# Vsechny pouzite knihovny jsou soucasti firmwaru CircuitPython pro Maker Badge
import board # Knihovna pro praci s deskou (popis dostupnych pinu apod.)
import digitalio # Knihovna pro praci s digitalnimi signaly 
import analogio # Knihovna por praci s analogovymi signaly
import touchio # Knihovna pro praci s dotykovymi tlacitky
import neopixel # Knihovna pro praci s adresovatelnymi RGB LED
import gc # Knihovna pro praci se spravou pameti
import terminalio # Knihovna pro praci s terminalem
import time # Knihovna pro praci s casem
import displayio # Knihovny pro praci s displejem
import adafruit_ssd1680
from adafruit_display_text import label

# Funkce pro zapis textu do konzole/terminalu
# vylepsena o vypis stavu volne RAM (Kod v CircuitPython muze byt hladovy)
def printm(text):
    print(f"RAM {gc.mem_free()} B:\t{text}")

# Funkce pro nastaveni vditelnosti vrstvy/objektu na displeji
# Graficke prvky na obrazovce jsou adresovatelne v jednoduchem „DOM“ principu
# Objekt zviditlenime tak, ze jej pridame, nebo odstranime do rodicovskeho objektu
def nastav_viditelnost_vrstvy(viditelna, rodic, vrstva):
    try:
        if viditelna:
            rodic.append(vrstva)
        else:
            rodic.remove(vrstva)
    except ValueError:
        pass

# Funkce pro aktivaci vrstvy/objektu
# Pomoci vyse vytvorene funkce projdeme vsechny potomky rodice a zneviditelnime je
# Pote zviditelnime jen toho potomka/vrstvu, ktereho zrovna potrebujeme
def aktivuj_gui_vrstvu(rodic, vrstva):
    for _vrstva in rodic:
        nastav_viditelnost_vrstvy(False, rodic, _vrstva)
    nastav_viditelnost_vrstvy(True, rodic, vrstva)

# Funkce pro vytvoreni textu na obrazovce, ktery bude zapouzdreny v objektu Group (vice pozdeji v kodu)
# V objektu Group by tak mohlo byt vicero textu se spolecnymi rodicovskymi parametery
# jako velikost, souradnice atp. My ale pracujeme jen s jednim textem
def vytvor_textovy_objekt(text, velikost, barva, x, y):
    objekt = displayio.Group(scale=velikost, x=x, y=y)
    text_obj = label.Label(terminalio.FONT, text=text, color=barva)
    objekt.append(text_obj)
    return objekt

# Funkce pro zjisteni stavu akumulatoru
# Akumulator je pripojeny skrze A/D prevodnik na pin GPIO6
# Pro snizeni napeti se pouziva delic napeti se dvema 10 kOhm rezistory
# Napeti je tedy bezpecne snizeno na polovinu (koeficient 2)
# Obvod delice by v klidu zbytecne spaloval elektrickou energii,
# a tak jej aktivujeme pomoci tranzistoru pripojeneho na GPIO14
def ziskej_stav_baterie():
    koeficient_delice = 2 # Delic napeti snizuje napeti na polovinu
    baterie_en.value = False # # Tranzistor sepne obvod delice napeti nastavenim pinu GPIO14 na nizky stav
    raw = baterie_adc.value # Ziskame hodnotu  /A/D
    baterie_en.value = True # Obvod odpojime nastavenim vysokeho stavu
    # Udaj z A/D CircuitPython vraci v rozsahu 0-65535 nehlede na skutecne rozliseni A/D na cipu
    # Surovou hodnotu prepocteme zpet na napeti s predpokladem, ze hodnota 65535 odpovida napeti 3,3V (rozsah prevodniku)
    napeti = raw * (3.3 / 65536)
    return napeti * koeficient_delice, napeti, raw

printm("Fakticky zacatek programu")

# ********** NASTAVENI EINK DISPLEJE **********
# Konfigurace komunikacnich a napajecich pinu
displej_spi = board.SPI() 
displej_cs = board.D41
displej_dc = board.D40
displej_reset = board.D39
displej_busy = board.D42
displej_en = digitalio.DigitalInOut(board.D16)
displej_en.direction = digitalio.Direction.OUTPUT

# Aktivace napajeni einku a konfigurace jeho sbernice SPI
displej_en.value = False # Tranzistor sepne napajeni einku nastavenim pinu GPIO16 na nizky stav
displayio.release_displays()
display_bus = displayio.FourWire(
    displej_spi,
    command=displej_dc,
    chip_select=displej_cs,
    reset=displej_reset,
    baudrate=1000000,
)
time.sleep(1)

# Konfigurace zakladnich parametru einku a vytvoreni prazdne pomocne bitmapy pro dve psoledni obrazovky
displej_sirka = 250
displej_vyska = 122
displej_cerna = 0x000000
displej_bila = 0xFFFFFF
displej_paleta = displayio.Palette(1)
displej_paleta[0] = displej_bila
displej_pozadi = displayio.Bitmap(displej_sirka, displej_vyska, 1)

# Konfigurace obvladace einku a vytvoreni objektu eink displeje
displej = adafruit_ssd1680.SSD1680(
    display_bus,
    width=displej_sirka,
    height=displej_vyska,
    rotation=270,
    busy_pin=displej_busy,
    # Ve vychozim stavu ovladac umozni prekresleni displeje cca jen jednou za 180 sekund
    # Je to doporucena hodnota od vyrobce, ktera ma zajistit vysokou trvanlivost
    # Pro rychlou praci s badgem by to ale bylo neergonomicke
    # Timto prikazem si vynutime snizeni prodlevy na 100 ms
    # za cenu potencialniho snizeni trvanlivosti displeje
    seconds_per_frame=0.1,
)

# ********** KONFIGURACE PINU PRO CTENI STAVU AKUMULATORU **********
baterie_en = digitalio.DigitalInOut(board.D14)
baterie_en.direction = digitalio.Direction.OUTPUT
baterie_adc = analogio.AnalogIn(board.D6)
ziskej_stav_baterie() # Uvodni cteni z A/D „na prazdno“ pro stabilizaci


# ********** KONFIGURACE PETI DOTYKOVYCH TLACITEK **********
tlacitka_citlivost = 20000
tlacitko1 = touchio.TouchIn(board.D5)
tlacitko1.threshold = tlacitka_citlivost
tlacitko2 = touchio.TouchIn(board.D4)
tlacitko2.threshold = tlacitka_citlivost
tlacitko3 = touchio.TouchIn(board.D3)
tlacitko3.threshold = tlacitka_citlivost
tlacitko4 = touchio.TouchIn(board.D2)
tlacitko4.threshold = tlacitka_citlivost
tlacitko5 = touchio.TouchIn(board.D1)
tlacitko5.threshold = tlacitka_citlivost

# ********** KONFIGURACE MATICE CTYR MODULU ADRESOVATELNYCH RGB LED **********
led_pin = board.D18
led_matrix = neopixel.NeoPixel(led_pin, 4, brightness=0.1, auto_write=False)

# RGB barvy pro LED
led_vypnuto = (0, 0, 0)
led_cervena = (255, 0, 0)
led_zelena = (0, 255, 0)
led_modra = (0, 0, 255)
led_fialova = (255, 0, 255)


# ********** VYTVORENI PETI HLAVNICH OBRAZOVEK/VRSTEV MEZI KTERYMI BUDEME PREPINAT **********
# Mezi obrazovkami budeme prepinat pomoci dotykovych plosek na spodnim okraji Maker Badge
# Knihovna Displayio umoznuje zakladni logickou organizaci objektu na obrazovce. Souvisejici casti na
# obrazovce proto zapouzdrime do skupinoveho objektu Group a TileGrid, ktere pak budeme moci
# snadno zapinat a vypinat, menit jejich obsah atp.Zakladnim rodicem vsech techto objektu
# na obrazovce bude kontejner 
kontejner = displayio.Group()
printm("Hlavni kontejner vytvoreny")

# Ted vytvorime objekt prvni obrazovky ze souboru obrazovka1.bmp
# Je to obrazek nasi formalni vizitky
obrazovka1_bmp = displayio.OnDiskBitmap("/obrazovky/obrazovka1.bmp")
obrazovka1 = displayio.TileGrid(obrazovka1_bmp, pixel_shader=obrazovka1_bmp.pixel_shader)
printm("Prvni obrazovka vytvorena")

# Ted vytvorime objekt druhe obrazovky ze souboru obrazovka2.bmp
# Je to obrazek nasi seznamkove vizitky vecer do baru
obrazovka2_bmp = displayio.OnDiskBitmap("/obrazovky/obrazovka2.bmp")
obrazovka2 = displayio.TileGrid(obrazovka2_bmp, pixel_shader=obrazovka2_bmp.pixel_shader)
printm("Druha obrazovka vytvorena")

# Ted vytvorime objekt treti obrazovky ze souboru obrazovka3.bmp
# Je to obrazek nocni vizitky, kdy uz jsme spolecensky unaveni a chceme, aby nam nekdo zavolal taxik
obrazovka3_bmp = displayio.OnDiskBitmap("/obrazovky/obrazovka3.bmp")
obrazovka3 = displayio.TileGrid(obrazovka3_bmp, pixel_shader=obrazovka3_bmp.pixel_shader)
printm("Treti obrazovka vytvorena")

# Ctvrtou obrazovku vytvorime dynamicky za behu
# Je to jen ukazka. Kazdy element je zpetne adresovatelny a upravitelny
# Dodatecne tedy muzeme menit i text aj.
obrazovka4_bmp = displayio.OnDiskBitmap("/obrazovky/obrazovka4.bmp")
obrazovka4 = displayio.TileGrid(obrazovka4_bmp, pixel_shader=obrazovka4_bmp.pixel_shader)
printm("Ctvrta obrazovka vytvorena")

# Patou obrazovku vytvorime take dynamicky
# Bude se na ni po stisku na 5. tlacitko zobrazovat aktualni stav akumulatoru 
obrazovka5 = displayio.Group()
obrazovka5.append(displayio.TileGrid(displej_pozadi, pixel_shader=displej_paleta))
obrazovka5.append(vytvor_textovy_objekt("Stav baterie", 2, displej_cerna, 5, 20))
obrazovka5.append(vytvor_textovy_objekt("0.000 V", 3, displej_cerna, 5, 60))
printm("Pata obrazovka vytvorena")

# Ve vychozim stavu zobrazime 1. obrazovku
# Nastavime tedy tuto vrstvu na viditelnou, ostatni skryjeme
# a dame povel ovladaci, at ji vykresli na eink
# Vsimnete si stromove architektury kontejner->obrazovka
# Obrazovky aktivaci vlastne pridavame, nebo odstranujeme
# z hlavniho kontejneru, ktery posilame do einku 
aktivuj_gui_vrstvu(kontejner, obrazovka1)
displej.show(kontejner)
displej.refresh()
printm("Prvni obrazovka zobrazena")

# ********** NEKONECNA SMYCKA PROGRAMU **********
# Analogie loop() z Arduina
# Ze smycky vyskocime leda pri chybe programu,
# anebo vypnutim napajeni pomoci prepinace
# Prave rucni vypnuti predpokladame,
# pro jednoduchost kodu totiz neprechazime do usporneho rezimu
# a cip ESP32 tedy bezi naplno a splauje elektrinu
while True:
    # Pri stisku 1. tlacitka vypneme RGB LED a zobrazime 1. obrazovku
    if tlacitko1.value:
        printm("Stisk tlacitka 1")
        led_matrix.fill(led_vypnuto)
        led_matrix.show()
        aktivuj_gui_vrstvu(kontejner, obrazovka1) 
        displej.show(kontejner)
        displej.refresh()
        printm("Prvni obrazovka zobrazena")   
    # Pri stisku 2. tlacitka nastavime na RGB LED cervenou a zobrazime 2. obrazovku
    if tlacitko2.value:
        printm("Stisk tlacitka 2")
        led_matrix.fill(led_cervena)
        led_matrix.show()
        aktivuj_gui_vrstvu(kontejner, obrazovka2)
        displej.show(kontejner)
        displej.refresh()
        printm("Druha obrazovka zobrazena")
    # Pri stisku 3. tlacitka nastavime na RGB LED zelenou a zobrazime 3. obrazovku
    if tlacitko3.value:
        printm("Stisk tlacitka 3")
        led_matrix.fill(led_zelena)
        led_matrix.show()
        aktivuj_gui_vrstvu(kontejner, obrazovka3)
        displej.show(kontejner)
        displej.refresh()
        printm("Treti obrazovka zobrazena")
    # Pri stisku 4. tlacitka nastavime na RGB LED modrou a zobrazime 4. obrazovku
    if tlacitko4.value:
        printm("Stisk tlacitka 4")
        led_matrix.fill(led_modra)
        led_matrix.show()
        aktivuj_gui_vrstvu(kontejner, obrazovka4)
        displej.show(kontejner)
        displej.refresh()
        printm("Ctvrta obrazovka zobrazena")
    # Pri stisku 5. tlacitka nastavíme RGB LED na fialovou, zmerime napeti akumulatoru,
    # dynamicky upravime 5. obrazovku a zobrazime ji
    if tlacitko5.value:
        printm("Stisk tlacitka 5")
        led_matrix.fill(led_fialova)
        led_matrix.show()
        # Zmerime napeti v akumulatoru pomoci A/D prevodniku
        # Deska pouziva delic napeti se dvema 10 kOhm rezistory
        # A/D prevodnik proto cte napeti snizene na polovinu
        # Funkce pro prehlednost vraci vsechny hodnoty
        napeti, napeti_delic, raw = ziskej_stav_baterie()
        printm(f"Stav akumulatoru: " +
            f"RAW hodnota z A/D prevodniku: {raw}\t" +
            f"Napeti za delicem: {napeti_delic} V\t" +
            f"Napeti akumulatoru: {napeti} V"
        )
        # Priklad dodatecne upravy objektu na obrazovce za behu:
        # Obrazovka 5 se sklada ze tri objektu (bile pozadi, prvni radek, druhy radek)
        # Prejdeme tedy na treti objekt (index 2), coz je dalsi objekt,
        # ktery obsahuje konecne jeden GUI element label (index 0)
        # u ktereho adekvatne zmenime parametr text
        obrazovka5[2][0].text = str(f"{napeti:.3f} V")        
        aktivuj_gui_vrstvu(kontejner, obrazovka5)
        displej.show(kontejner)
        displej.refresh()
        printm("Pata obrazovka zobrazena")



        # Code created by Matouš Papoušek
        # Doufám že FW poslouží !!! :)