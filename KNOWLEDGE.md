# KNOWLEDGE

## Neden Kodes %6 ile birinci?
Kodese giriş atışların ~%3,7'sinde olur: Kodese-Git karesi (1/40), 3 üst üste çift (~1/216) ve 2 "Kodese git"
kartı. Hepsi tek kareye (10) yığılır; normal ziyaret (%2,5) ile birleşince taban değerin ~2,5 katı çıkar.

## Neden Illinois Ave en çok gelinen mülk? (~%3,17)
Kodesten çıkan piyon 12-22 bandına dağılır (ortalama 7 adım), bu bandı geçenler Kırmızı grubun sonunda toplanır;
Şans'taki "Illinois'e git" kartı 24'e ek ağırlık verir. İstasyonlar (Reading, B&O) "en yakın istasyon" ve
"Reading'e git" kartlarıyla hemen arkadan gelir.

## Neden Turuncu/Kırmızı ve New York Ave?
ROI = P(iniş) x 3 evli kira x 3 rakip / (fiyat + 3 ev maliyeti). Turuncu 16-19 Kodes çıkış bandındadır,
3 evde 550-600$ kira için yatırım yalnızca ~480-500$ → ~9,7 turda geri döner. Kırmızı (21-24) ikinci,
Koyu Mavi üçüncüdür. Boardwalk tekil ROI'de New York ile başa baştır ama mülk başına ~1000$ ister ve
grupta yalnızca 2 kare vardır. Kahverengi düşük kira, İstasyon/Hizmet düşük kira çarpanı yüzünden sondadır.

## Model varsayımları / sadeleştirmeler
- Sayılan olay: atış sonu durulan kare. Kodes'te bekleyen başarısız atış sayılmaz (Markov "iniş" tanımı).
- Kodese-Git karesi (30) sonuç tablosunda her zaman %0'dır.
- Oyunda açık artırma, takas ve ev stok sınırı yoktur; Gelir Vergisi sabit 200$ ödenir.
- ROI: istasyon 2 adet (50$), hizmet 2 adet (10 x 7) varsayımı; 3 rakip; 3 ev.
- Sonuçlar yaklaşık: 100.000 oyunda ikinci ondalık ±0,02 puan oynar.

## Teknik notlar
- Windows'ta ANSI için `SetConsoleMode(..., ENABLE_VIRTUAL_TERMINAL_PROCESSING)`; stdout UTF-8 yapılır.
- `wt -d "%CD%."` sondaki nokta, kök dizinde `\"` kaçış hatasını önler.
- `multiprocessing` Windows'ta spawn kullanır; giriş noktası `if __name__ == "__main__"` altında olmalıdır.
- Hücre içeriği ANSI kaçışları nedeniyle `visible_len` ile ölçülür; aksi hâlde tahta kayar.
