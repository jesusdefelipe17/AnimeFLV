from animeflv import AnimeFLV
with AnimeFLV() as api:
        # Buscar series que coincidan con el nombre introducido
        elements = api.search(input("Escribe una serie: "))
        for i, element in enumerate(elements):
            print(f"{i}, {element.title}")
        try:
               seleccion = int(input("Selecciona una opcion: "))
               info = api.get_anime_info(elements[seleccion].id)
               info.episodes.reverse()
               for j, episode in enumerate(info.episodes):
                     print(f"{j}, | Episodio - {episode.id}")
                     indice_episodio = int(input("Selecciona un epidosdio: "))
                     serie = elements[seleccion].id
                     capitulo = info.episodes[indice_episodio].id
                     resultados = api.get_links(serie,capitulo)
                     for resultado in resultados:
                         print(f"{resultado.server} : {resultado.url}")        
        except print(0):
                pass
        
        