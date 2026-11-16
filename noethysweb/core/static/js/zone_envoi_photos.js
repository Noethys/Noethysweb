//  Copyright (c) 2019-2026 Ivan LUCAS.
//  Noethysweb, application de gestion multi-activités.
//  Distribué sous licence GNU GPL.
//
//  Zone d'envoi de photos : glisser-déposer, aperçus, réduction des images
//  dans le navigateur et envoi des fichiers un par un avec progression.

(function () {
    "use strict";

    var FORMATS_REDIMENSIONNABLES = ["image/jpeg", "image/png", "image/webp", "image/bmp"];

    function Formate_taille(octets) {
        if (octets < 1024 * 1024) {
            return Math.max(1, Math.round(octets / 1024)) + " Ko";
        }
        return (octets / (1024 * 1024)).toFixed(1).replace(".", ",") + " Mo";
    }

    function Creer(tag, classe, texte) {
        var element = document.createElement(tag);
        if (classe) { element.className = classe; }
        if (texte !== undefined) { element.textContent = texte; }
        return element;
    }

    // Lecture de la date de prise de vue (EXIF DateTimeOriginal) d'un JPEG
    function Lire_date_exif(fichier) {
        return new Promise(function (resolve) {
            if (fichier.type !== "image/jpeg") { resolve(null); return; }
            var lecteur = new FileReader();
            lecteur.onerror = function () { resolve(null); };
            lecteur.onload = function () {
                try { resolve(Analyser_exif(new DataView(lecteur.result))); }
                catch (e) { resolve(null); }
            };
            lecteur.readAsArrayBuffer(fichier.slice(0, 256 * 1024));
        });
    }

    function Analyser_exif(vue) {
        if (vue.getUint16(0) !== 0xFFD8) { return null; }
        var position = 2;
        while (position + 4 < vue.byteLength) {
            var marqueur = vue.getUint16(position);
            var longueur = vue.getUint16(position + 2);
            if (marqueur === 0xFFE1 && vue.getUint32(position + 4) === 0x45786966) {
                return Lire_tiff(vue, position + 10);
            }
            if ((marqueur & 0xFF00) !== 0xFF00) { return null; }
            position += 2 + longueur;
        }
        return null;
    }

    function Lire_tiff(vue, debut) {
        var little = vue.getUint16(debut) === 0x4949;
        var lire16 = function (p) { return vue.getUint16(p, little); };
        var lire32 = function (p) { return vue.getUint32(p, little); };
        var Chercher_tag = function (ifd, tag) {
            var nbre = lire16(ifd);
            for (var i = 0; i < nbre; i++) {
                var entree = ifd + 2 + i * 12;
                if (lire16(entree) === tag) { return entree; }
            }
            return null;
        };
        var ifd0 = debut + lire32(debut + 4);
        var pointeur_exif = Chercher_tag(ifd0, 0x8769);
        if (pointeur_exif === null) { return null; }
        var ifd_exif = debut + lire32(pointeur_exif + 8);
        var entree_date = Chercher_tag(ifd_exif, 0x9003) || Chercher_tag(ifd_exif, 0x9004);
        if (entree_date === null) { return null; }
        var offset = debut + lire32(entree_date + 8);
        var texte = "";
        for (var i = 0; i < 19; i++) { texte += String.fromCharCode(vue.getUint8(offset + i)); }
        return /^\d{4}:\d{2}:\d{2} \d{2}:\d{2}:\d{2}$/.test(texte) ? texte : null;
    }

    // Chargement d'une image en tenant compte de l'orientation EXIF
    function Charger_image(fichier) {
        if (window.createImageBitmap) {
            return createImageBitmap(fichier, {imageOrientation: "from-image"}).catch(function () {
                return Charger_image_html(fichier);
            });
        }
        return Charger_image_html(fichier);
    }

    function Charger_image_html(fichier) {
        return new Promise(function (resolve, reject) {
            var url = URL.createObjectURL(fichier);
            var image = new Image();
            image.onload = function () { URL.revokeObjectURL(url); resolve(image); };
            image.onerror = function () { URL.revokeObjectURL(url); reject(new Error("Image illisible")); };
            image.src = url;
        });
    }

    // Réduction d'une image si elle dépasse la dimension maximale
    function Reduire_image(fichier, dimension_max) {
        if (!dimension_max || FORMATS_REDIMENSIONNABLES.indexOf(fichier.type) === -1) {
            return Promise.resolve(fichier);
        }
        return Charger_image(fichier).then(function (image) {
            var largeur = image.width, hauteur = image.height;
            if (Math.max(largeur, hauteur) <= dimension_max) { return fichier; }
            var ratio = dimension_max / Math.max(largeur, hauteur);
            var canvas = document.createElement("canvas");
            canvas.width = Math.round(largeur * ratio);
            canvas.height = Math.round(hauteur * ratio);
            canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
            var type = fichier.type === "image/png" ? "image/png" : "image/jpeg";
            return new Promise(function (resolve) {
                canvas.toBlob(function (blob) {
                    if (!blob) { resolve(fichier); return; }
                    var nom = fichier.name;
                    if (type === "image/jpeg" && !/\.jpe?g$/i.test(nom)) { nom = nom.replace(/\.[^.]*$/, "") + ".jpg"; }
                    resolve(new File([blob], nom, {type: type, lastModified: fichier.lastModified}));
                }, type, 0.88);
            });
        }).catch(function () {
            return fichier;
        });
    }

    function ZoneEnvoi(racine) {
        this.racine = racine;
        this.url = racine.dataset.url;
        this.url_fin = racine.dataset.urlFin;
        this.dimension_max = parseInt(racine.dataset.dimensionMax || "0", 10);
        this.taille_max = parseFloat(racine.dataset.tailleMax || "10") * 1024 * 1024;
        this.libelle_bouton = racine.dataset.libelleBouton || "Envoyer";
        this.extra = JSON.parse(racine.dataset.extra || "{}");
        this.csrf = racine.querySelector("[name=csrfmiddlewaretoken]").value;
        this.elements = [];
        this.en_cours = false;

        this.input = racine.querySelector(".zone-envoi-input");
        this.depot = racine.querySelector(".zone-envoi-depot");
        this.liste = racine.querySelector(".zone-envoi-liste");
        this.resume = racine.querySelector(".zone-envoi-resume");
        this.actions = racine.querySelector(".zone-envoi-actions");
        this.bouton_envoyer = racine.querySelector(".zone-envoi-envoyer");
        this.bouton_effacer = racine.querySelector(".zone-envoi-effacer");
        this.progression = racine.querySelector(".zone-envoi-progression");
        this.barre = racine.querySelector(".zone-envoi-progression .progress-bar");
        this.texte_progression = racine.querySelector(".zone-envoi-progression-texte");
        this.message = racine.querySelector(".zone-envoi-message");

        this.Installer();
        this.Actualiser();
    }

    ZoneEnvoi.prototype.Installer = function () {
        var self = this;
        this.input.addEventListener("change", function () {
            self.Ajouter(self.input.files);
            self.input.value = "";
        });
        ["dragenter", "dragover"].forEach(function (evt) {
            self.depot.addEventListener(evt, function (e) {
                e.preventDefault();
                if (!self.en_cours) { self.depot.classList.add("survol"); }
            });
        });
        ["dragleave", "drop"].forEach(function (evt) {
            self.depot.addEventListener(evt, function (e) {
                e.preventDefault();
                self.depot.classList.remove("survol");
            });
        });
        this.depot.addEventListener("drop", function (e) {
            if (!self.en_cours && e.dataTransfer) { self.Ajouter(e.dataTransfer.files); }
        });
        this.depot.addEventListener("keydown", function (e) {
            if (e.key === "Enter" || e.key === " ") { e.preventDefault(); self.input.click(); }
        });
        this.bouton_effacer.addEventListener("click", function () { self.Effacer(); });
        this.bouton_envoyer.addEventListener("click", function () { self.Envoyer(); });
    };

    ZoneEnvoi.prototype.Ajouter = function (fichiers) {
        if (this.en_cours) { return; }
        for (var i = 0; i < fichiers.length; i++) {
            var fichier = fichiers[i];
            var element = {fichier: fichier, statut: "attente", erreur: null, apercu: null, progression: 0};
            if (!fichier.type || fichier.type.indexOf("image/") !== 0) {
                element.statut = "invalide";
                element.erreur = "Format non accepté";
            } else {
                element.apercu = URL.createObjectURL(fichier);
            }
            this.elements.push(element);
        }
        this.message.textContent = "";
        this.Actualiser();
    };

    ZoneEnvoi.prototype.Retirer = function (element) {
        if (this.en_cours) { return; }
        if (element.apercu) { URL.revokeObjectURL(element.apercu); }
        this.elements.splice(this.elements.indexOf(element), 1);
        this.Actualiser();
    };

    ZoneEnvoi.prototype.Effacer = function () {
        if (this.en_cours) { return; }
        this.elements.forEach(function (element) {
            if (element.apercu) { URL.revokeObjectURL(element.apercu); }
        });
        this.elements = [];
        this.message.textContent = "";
        this.Actualiser();
    };

    ZoneEnvoi.prototype.A_envoyer = function () {
        return this.elements.filter(function (element) { return element.statut === "attente"; });
    };

    ZoneEnvoi.prototype.Actualiser = function () {
        var self = this;
        this.liste.textContent = "";
        this.elements.forEach(function (element) {
            var vignette = Creer("div", "zone-envoi-vignette statut-" + element.statut + (element.erreur ? " avec-erreur" : ""));
            var image = Creer("div", "zone-envoi-image");
            if (element.apercu && element.statut !== "invalide") {
                image.style.backgroundImage = "url('" + element.apercu + "')";
            } else {
                image.appendChild(Creer("i", "fa fa-exclamation-triangle"));
            }
            if (element.statut === "ok") { image.appendChild(Creer("span", "zone-envoi-badge fa fa-check")); }
            vignette.appendChild(image);

            var infos = Creer("div", "zone-envoi-infos");
            var nom = Creer("span", "zone-envoi-nom", element.fichier.name);
            nom.title = element.fichier.name;
            infos.appendChild(nom);
            if (!self.en_cours && element.statut !== "ok") {
                var retirer = Creer("button", "zone-envoi-retirer fa fa-times");
                retirer.type = "button";
                retirer.title = "Retirer";
                retirer.setAttribute("aria-label", "Retirer " + element.fichier.name);
                retirer.addEventListener("click", function () { self.Retirer(element); });
                infos.appendChild(retirer);
            } else if (element.statut === "envoi") {
                infos.appendChild(Creer("span", "zone-envoi-pourcent", Math.round(element.progression * 100) + " %"));
            } else if (element.statut === "attente") {
                infos.appendChild(Creer("span", "zone-envoi-pourcent", "en attente"));
            }
            vignette.appendChild(infos);

            if (self.en_cours || element.statut === "ok") {
                var barre = Creer("div", "zone-envoi-mini-barre");
                var remplissage = Creer("span");
                remplissage.style.width = (element.statut === "ok" ? 100 : Math.round(element.progression * 100)) + "%";
                barre.appendChild(remplissage);
                vignette.appendChild(barre);
            }
            if (element.erreur) { vignette.appendChild(Creer("div", "zone-envoi-erreur", element.erreur)); }
            self.liste.appendChild(vignette);
        });

        var a_envoyer = this.A_envoyer();
        var total = a_envoyer.reduce(function (somme, element) { return somme + element.fichier.size; }, 0);
        this.resume.textContent = this.elements.length ? a_envoyer.length + " photo(s) · " + Formate_taille(total) : "";
        this.depot.classList.toggle("compacte", this.elements.length > 0);
        this.actions.style.display = this.elements.length && !this.en_cours ? "" : "none";
        this.bouton_envoyer.disabled = a_envoyer.length === 0;
        this.bouton_envoyer.querySelector(".libelle").textContent = this.libelle_bouton + (a_envoyer.length ? " (" + a_envoyer.length + ")" : "");
        this.racine.classList.toggle("en-cours", this.en_cours);
    };

    ZoneEnvoi.prototype.Envoyer = function () {
        var self = this;
        var a_envoyer = this.A_envoyer();
        if (!a_envoyer.length || this.en_cours) { return; }
        this.en_cours = true;
        this.message.textContent = "";
        this.progression.style.display = "";
        this.Actualiser();

        var total = a_envoyer.length;
        var index = 0;

        var Suivant = function () {
            if (index >= total) { self.Terminer(); return; }
            var element = a_envoyer[index];
            index += 1;
            self.texte_progression.textContent = "Envoi " + index + " / " + total;
            element.statut = "envoi";
            element.erreur = null;
            self.Actualiser();
            self.Envoyer_element(element, function (fraction) {
                element.progression = fraction;
                self.barre.style.width = Math.round(((index - 1 + fraction) / total) * 100) + "%";
                self.Actualiser();
            }).then(Suivant);
        };
        Suivant();
    };

    ZoneEnvoi.prototype.Envoyer_element = function (element, sur_progression) {
        var self = this;
        return Promise.all([
            Reduire_image(element.fichier, this.dimension_max),
            Lire_date_exif(element.fichier)
        ]).then(function (resultats) {
            var fichier = resultats[0];
            var date_prise = resultats[1];
            if (fichier.size > self.taille_max) {
                element.statut = "erreur";
                element.erreur = "Fichier trop volumineux (" + Formate_taille(fichier.size) + ")";
                return;
            }
            var donnees = new FormData();
            donnees.append("fichier", fichier, fichier.name);
            if (date_prise) { donnees.append("date_prise", date_prise); }
            Object.keys(self.extra).forEach(function (cle) { donnees.append(cle, self.extra[cle]); });

            return new Promise(function (resolve) {
                var xhr = new XMLHttpRequest();
                xhr.open("POST", self.url);
                xhr.setRequestHeader("X-CSRFToken", self.csrf);
                xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
                xhr.upload.addEventListener("progress", function (e) {
                    if (e.lengthComputable) { sur_progression(e.loaded / e.total); }
                });
                xhr.onload = function () {
                    var reponse = {};
                    try { reponse = JSON.parse(xhr.responseText); } catch (e) {}
                    if (xhr.status === 200 && reponse.ok) {
                        element.statut = "ok";
                        element.progression = 1;
                    } else {
                        element.statut = "erreur";
                        element.erreur = reponse.erreur || "Erreur du serveur (" + xhr.status + ")";
                    }
                    resolve();
                };
                xhr.onerror = function () {
                    element.statut = "erreur";
                    element.erreur = "Connexion interrompue";
                    resolve();
                };
                xhr.send(donnees);
            });
        });
    };

    ZoneEnvoi.prototype.Terminer = function () {
        var nbre_ok = this.elements.filter(function (element) { return element.statut === "ok"; }).length;
        var nbre_erreurs = this.elements.filter(function (element) { return element.statut === "erreur"; }).length;
        this.barre.style.width = "100%";
        if (nbre_ok && !nbre_erreurs) {
            this.texte_progression.textContent = "Envoi terminé";
            window.location.href = this.url_fin;
            return;
        }
        this.en_cours = false;
        this.progression.style.display = "none";
        // Les fichiers en erreur repassent en attente pour pouvoir être renvoyés
        this.elements.forEach(function (element) {
            if (element.statut === "erreur") { element.statut = "attente"; element.progression = 0; }
        });
        this.Actualiser();
        this.message.textContent = "";
        if (nbre_ok) {
            this.message.appendChild(document.createTextNode(nbre_ok + " photo(s) envoyée(s), " + nbre_erreurs + " en erreur. Vous pouvez réessayer ou "));
            var lien = Creer("a", "", "continuer sans ces photos");
            lien.href = this.url_fin;
            this.message.appendChild(lien);
            this.message.appendChild(document.createTextNode("."));
        } else {
            this.message.textContent = "Aucune photo n'a pu être envoyée. Vérifiez les erreurs puis réessayez.";
        }
    };

    function Initialiser() {
        var zones = document.querySelectorAll(".zone-envoi");
        for (var i = 0; i < zones.length; i++) {
            if (!zones[i].zoneEnvoi) { zones[i].zoneEnvoi = new ZoneEnvoi(zones[i]); }
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", Initialiser);
    } else {
        Initialiser();
    }
})();
