import os
import tweepy
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import time
from dotenv import load_dotenv

load_dotenv()

auth = tweepy.OAuthHandler(
    os.getenv('TWITTER_API_KEY'),
    os.getenv('TWITTER_API_SECRET')
)

auth.set_access_token(
    os.getenv('TWITTER_ACCESS_TOKEN'),
    os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
)

api = tweepy.Client(
    bearer_token=os.getenv('TWITTER_BEARER_TOKEN'),
    access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
    access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
    consumer_key=os.getenv('TWITTER_API_KEY'),
    consumer_secret=os.getenv('TWITTER_API_SECRET'),
)

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

creds_json = os.getenv('GOOGLE_SHEETS_CREDS')
creds_dict = json.loads(creds_json)

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

client = gspread.authorize(creds)
sheet = client.open_by_key(os.getenv('GOOGLE_SHEETS_KEY'))

worksheet = sheet.sheet1

records = worksheet.get_all_records()

# Filtrar los registros que no han sido posteados
empty_posted_records = [record for record in records if record['Posted'] == '']


# Si hay registros sin postear
if empty_posted_records:
    # Encontrar el primer ID sin postear
    first_unposted_id = empty_posted_records[0]['ID']

    # Filtrar los registros que pertenecen a ese ID y ordenar por Sequence
    tweets_to_post = sorted([record for record in records if record['ID'] == first_unposted_id], key=lambda x: x['Sequence'])

    first_tweet_id = None  # Guardar el tweet_id del primer tweet

    for i, tweet in enumerate(tweets_to_post):
        index = records.index(tweet)
        
        if i == 0:
            # Para el primer tweet: incluir toda la información
            text = (
                str(tweet['Text']) + ' '
                + str(tweet['Hashtags'])
            )
            
        else:
            # Para los tweets en el hilo: solo incluir la columna 'Story'
            text = str(tweet['Text'])
        


        #AQUÍ EMPIEZA MI PRUEBA POR ANALIZAR
    # Verificar si el tweet excede el límite de 280 caracteres
        if len(text) > 280:
            # Si el tweet es demasiado largo, actualizar el registro en la hoja
            worksheet.update_cell(index + 2, 6, "too large")  # Columna "Posted"
            
            # Marcar todos los tweets del hilo como "No" para pasar al siguiente ID
            for hilo_tweet in tweets_to_post:
                hilo_index = records.index(hilo_tweet)
                worksheet.update_cell(hilo_index + 2, 5, "No")  # Columna "Posted"
            
            # Filtrar los registros que no tengan "No" en "Posted" y actualizar el array tweets_to_post
            tweets_to_post = [record for record in tweets_to_post if record['Posted'] != "No"]
            
            # Saltar al siguiente ID sin postear el hilo
            first_unposted_id = empty_posted_records[0]['ID']
            
            # Filtrar los registros que pertenecen a ese ID y ordenar por Sequence
            tweets_to_post = sorted([record for record in records if record['ID'] == first_unposted_id], key=lambda x: x['Sequence'])
            
            break
#AQUÍ TERMINA MI PRUEBA POR ANALIZAR



        # Publicar el tweet
        if first_tweet_id is None:
            # Si es el primer tweet, no enlazar a nada
            post_result = api.create_tweet(text=text)
            first_tweet_id = post_result.data['id']
        else:
            # Si no es el primer tweet, enlazar al tweet anterior
            post_result = api.create_tweet(text=text, in_reply_to_tweet_id=first_tweet_id)
            first_tweet_id = post_result.data['id']
        
        tweet_id = post_result.data['id']
        print(f"Tweet publicado con ID: {tweet_id}")
        
        # Actualizar el registro en la hoja
        worksheet.update_cell(index + 2, 5, "Yes")  # Columna "Posted"
        worksheet.update_cell(index + 2, 6, tweet_id)  # Columna "Tweet ID"
        
        # Esperar 3 segundos antes de publicar el siguiente tweet en el hilo
        time.sleep(3)

else:
    print("No se encontró ningún registro con 'Posted' vacío.")
