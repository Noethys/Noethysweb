# -*- coding: utf-8 -*-
#  Copyright (c) 2019-2026 Ivan LUCAS.
#  Noethysweb, application de gestion multi-activités.
#  Distribué sous licence GNU GPL.

"""
Backend d'envoi d'emails via Microsoft 365 (API Microsoft Graph + OAuth2 client credentials).

Prérequis côté Microsoft Entra ID (portail Azure) :
  1. Inscriptions d'applications > Nouvelle inscription (compte unique du tenant).
  2. Autorisations d'API > Microsoft Graph > Autorisations d'application > Mail.Send,
     puis "Accorder le consentement administrateur".
  3. Certificats & secrets > Nouveau secret client (noter la VALEUR, pas l'ID).
  4. Recommandé : limiter l'application à la seule boîte d'envoi avec
     New-ApplicationAccessPolicy (Exchange Online PowerShell) ou RBAC for Applications.

L'adresse d'expédition doit être une boîte aux lettres (utilisateur ou boîte partagée) du tenant.
"""

import base64, hashlib, logging, time
from email.utils import parseaddr
import requests
from django.core.cache import cache
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

URL_TOKEN = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
URL_SENDMAIL = "https://graph.microsoft.com/v1.0/users/{expediteur}/sendMail"
SCOPE = "https://graph.microsoft.com/.default"
TAILLE_MAX_REQUETE = 4 * 1024 * 1024  # Limite Graph : 4 Mo par requête (MIME encodé en base64)
NBRE_TENTATIVES = 4
TIMEOUT = 30


class ErreurMicrosoft365(Exception):
    pass


def Traduire_erreur(reponse):
    """ Renvoie un message d'erreur lisible à partir d'une réponse Microsoft """
    try:
        data = reponse.json()
    except ValueError:
        return "Erreur HTTP %s : %s" % (reponse.status_code, reponse.text[:300])

    # Erreur d'authentification Entra ID (endpoint token)
    if "error_description" in data:
        description = data["error_description"].split("\r\n")[0]
        if "AADSTS7000215" in description:
            return "Secret client invalide. Vérifiez que vous avez saisi la VALEUR du secret (et non son ID) et qu'il n'a pas expiré."
        if "AADSTS700016" in description:
            return "ID d'application (client) introuvable dans ce tenant. Vérifiez le Client ID et le Tenant ID."
        if "AADSTS90002" in description or "AADSTS900023" in description:
            return "Tenant ID invalide ou introuvable."
        return "Authentification Microsoft refusée : %s" % description

    # Erreur Graph
    erreur = data.get("error", {})
    code, message = erreur.get("code", ""), erreur.get("message", "")
    if code == "ErrorAccessDenied" or reponse.status_code == 403:
        return "Accès refusé par Microsoft 365 (%s). Vérifiez la permission d'application Mail.Send avec consentement administrateur, et la stratégie d'accès éventuellement appliquée à cette boîte." % message
    if code in ("ErrorInvalidUser", "MailboxNotEnabledForRESTAPI", "ResourceNotFound") or reponse.status_code == 404:
        return "Boîte aux lettres d'expédition introuvable dans le tenant Microsoft 365 (%s)." % message
    return "Erreur Microsoft 365 %s %s : %s" % (reponse.status_code, code, message)


class EmailBackend(BaseEmailBackend):

    def __init__(self, tenant_id=None, client_id=None, client_secret=None, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.tenant_id = (tenant_id or "").strip()
        self.client_id = (client_id or "").strip()
        self.client_secret = client_secret or ""
        self.session = None
        self.token = None

    def _cle_cache(self):
        empreinte = hashlib.sha256(("%s|%s|%s" % (self.tenant_id, self.client_id, self.client_secret)).encode("utf-8")).hexdigest()
        return "microsoft365_token_%s" % empreinte

    def _get_token(self, forcer=False):
        if not (self.tenant_id and self.client_id and self.client_secret):
            raise ErreurMicrosoft365("Paramètres Microsoft 365 incomplets (Tenant ID, Client ID et secret client requis).")

        cle = self._cle_cache()
        if not forcer:
            token = cache.get(cle)
            if token:
                return token

        reponse = self.session.post(URL_TOKEN.format(tenant_id=self.tenant_id), timeout=TIMEOUT, data={
            "client_id": self.client_id, "client_secret": self.client_secret,
            "scope": SCOPE, "grant_type": "client_credentials",
        })
        if reponse.status_code != 200:
            raise ErreurMicrosoft365(Traduire_erreur(reponse))
        data = reponse.json()
        token = data["access_token"]
        cache.set(cle, token, max(int(data.get("expires_in", 3600)) - 300, 60))
        return token

    def open(self):
        if self.session:
            return False
        self.session = requests.Session()
        try:
            self.token = self._get_token()
        except Exception:
            self.session.close()
            self.session = None
            raise
        return True

    def close(self):
        if self.session:
            self.session.close()
        self.session = None
        self.token = None

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        nouvelle_connexion = self.open()
        nbre_envois = 0
        try:
            for message in email_messages:
                try:
                    self._envoyer(message)
                    nbre_envois += 1
                except Exception as err:
                    logger.error("Microsoft 365 : %s" % err)
                    if not self.fail_silently:
                        raise
        finally:
            if nouvelle_connexion:
                self.close()
        return nbre_envois

    def _envoyer(self, message):
        if not message.recipients():
            return

        expediteur = parseaddr(message.from_email)[1]
        if not expediteur:
            raise ErreurMicrosoft365("Adresse d'expédition invalide : %s" % message.from_email)

        # Message MIME complet (pièces jointes, images intégrées, en-têtes de désinscription...)
        mime = message.message()
        # Les destinataires en Cci ne figurent pas dans les en-têtes : Graph les lit depuis le MIME
        if message.bcc:
            del mime["Bcc"]
            mime["Bcc"] = ", ".join(message.bcc)
        contenu = base64.b64encode(mime.as_bytes(linesep="\r\n"))
        if len(contenu) > TAILLE_MAX_REQUETE:
            raise ErreurMicrosoft365("Message trop volumineux pour Microsoft 365 (%.1f Mo une fois encodé, maximum 4 Mo). Réduisez la taille des pièces jointes." % (len(contenu) / 1024 / 1024))

        url = URL_SENDMAIL.format(expediteur=requests.utils.quote(expediteur))
        token_renouvele = False
        for tentative in range(NBRE_TENTATIVES):
            reponse = self.session.post(url, data=contenu, timeout=TIMEOUT, headers={
                "Authorization": "Bearer %s" % self.token, "Content-Type": "text/plain",
            })

            if reponse.status_code == 202:
                return

            # Token expiré ou révoqué : on le renouvelle une fois
            if reponse.status_code == 401 and not token_renouvele:
                self.token = self._get_token(forcer=True)
                token_renouvele = True
                continue

            # Limitation de débit (Exchange : 30 messages/minute par boîte) ou indisponibilité temporaire
            if reponse.status_code in (429, 503, 504) and tentative < NBRE_TENTATIVES - 1:
                try:
                    attente = int(reponse.headers.get("Retry-After", 0))
                except ValueError:
                    attente = 0
                attente = min(max(attente, 5 * (tentative + 1)), 120)
                logger.warning("Microsoft 365 : limitation de débit, nouvel essai dans %d s." % attente)
                time.sleep(attente)
                continue

            raise ErreurMicrosoft365(Traduire_erreur(reponse))

        raise ErreurMicrosoft365("Envoi impossible après %d tentatives (limitation de débit Microsoft 365)." % NBRE_TENTATIVES)
