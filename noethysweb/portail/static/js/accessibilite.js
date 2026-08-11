/**
 * Noethysweb — Réglages d'accessibilité RGAA 4.1
 */

(function () {
    "use strict";

    var CLE_STORAGE = "noethysweb_a11y";

    var DEFAUTS = {
        contraste:          "standard",
        daltonisme:         "aucun",
        taille_texte:       "normale",
        souligner_liens:    false,
        masquer_images:     false,
        police_dyslexie:    false,
        espacement_lettres: false,
        interlignage:       "normal",
        masque_lecture:     false,
        grandes_zones_clic: false,
        agrandir_curseur:   "normal",
        reduire_animations: false,
    };

    /* ------------------------------------------------------------------ */
    /* Filtres SVG daltonisme (matrices Machado et al.)                   */
    /* ------------------------------------------------------------------ */
    var FILTRES_SVG = {
        deuteranopie: "0.367 0.861 -0.228 0 0 0.280 0.673 0.047 0 0 -0.012 0.043 0.969 0 0 0 0 0 1 0",
        protanopie:   "0.152 1.053 -0.205 0 0 0.115 0.786 0.099 0 0 -0.004 -0.048 1.052 0 0 0 0 0 1 0",
        tritanopie:   "1.256 -0.077 -0.179 0 0 -0.078 0.931 0.148 0 0 0.005 0.691 0.304 0 0 0 0 0 1 0",
    };

    function injecterFiltresSVG() {
        if (document.getElementById("a11y-svg-filters")) return;
        var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
        svg.id = "a11y-svg-filters";
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("hidden", "");
        svg.setAttribute("width", "0");  // Force la largeur à 0 en attribut HTML
        svg.setAttribute("height", "0"); // Force la hauteur à 0 en attribut HTML
        svg.setAttribute("viewBox", "0 0 0 0");
        svg.style.cssText = "position:absolute;width:0;height:0;overflow:hidden;";
        var defs = "";
        Object.keys(FILTRES_SVG).forEach(function (type) {
            defs += '<filter id="a11y-filter-' + type + '" x="0" y="0" width="100%" height="100%">' +
                    '<feColorMatrix type="matrix" values="' + FILTRES_SVG[type] + '"/>' +
                    '</filter>';
        });
        svg.innerHTML = "<defs>" + defs + "</defs>";
        document.body.insertBefore(svg, document.body.firstChild);
    }

    /* ------------------------------------------------------------------ */
    /* localStorage                                                        */
    /* ------------------------------------------------------------------ */
    function lirePreferences() {
        try {
            var raw = localStorage.getItem(CLE_STORAGE);
            return raw ? Object.assign({}, DEFAUTS, JSON.parse(raw)) : Object.assign({}, DEFAUTS);
        } catch (e) {
            return Object.assign({}, DEFAUTS);
        }
    }

    function sauvegarderPreferences(prefs) {
        try {
            localStorage.setItem(CLE_STORAGE, JSON.stringify(prefs));
        } catch (e) {
            console.warn("Noethysweb a11y : impossible d'écrire dans localStorage.", e);
        }
    }

    /* ------------------------------------------------------------------ */
    /* Zone aria-live — RGAA 13.8                                         */
    /* ------------------------------------------------------------------ */
    function annoncerLecteurEcran(message) {
        var zone = document.getElementById("a11y-live-region");
        if (!zone) return;
        zone.textContent = "";
        setTimeout(function () { zone.textContent = message; }, 50);
    }

    /* ------------------------------------------------------------------ */
    /* Masque de lecture                                                   */
    /* Bande semi-transparente qui suit la position verticale de la souris */
    /* ------------------------------------------------------------------ */
    var masqueEl = null;

    function creerMasqueLecture() {
        if (masqueEl) return;
        masqueEl = document.createElement("div");
        masqueEl.id = "a11y-masque-lecture";
        masqueEl.setAttribute("aria-hidden", "true");
        masqueEl.style.cssText = [
            "position:fixed",
            "left:0",
            "width:100%",
            "height:2.5em",
            "background:rgba(255,255,150,0.25)",
            "border-top:2px solid rgba(200,180,0,0.4)",
            "border-bottom:2px solid rgba(200,180,0,0.4)",
            "pointer-events:none",
            "z-index:9999",
            "transition:top 0.05s linear",
        ].join(";");
        document.body.appendChild(masqueEl);
    }

    function supprimerMasqueLecture() {
        if (masqueEl) {
            masqueEl.remove();
            masqueEl = null;
        }
        document.removeEventListener("mousemove", deplacerMasque);
    }

    function deplacerMasque(e) {
        if (!masqueEl) return;
        var hauteur = parseFloat(masqueEl.style.height) || 40;
        masqueEl.style.top = (e.clientY - hauteur / 2) + "px";
    }

    function activerMasqueLecture(actif) {
        if (actif) {
            creerMasqueLecture();
            document.addEventListener("mousemove", deplacerMasque);
        } else {
            supprimerMasqueLecture();
        }
    }

    /* ------------------------------------------------------------------ */
    /* Masquer les images                                                  */
    /* Cache les <img> et insère leur texte alt comme remplacement visible */
    /* ------------------------------------------------------------------ */
    function appliquerMasquerImages(actif) {
        /* Retirer les remplacements précédents */
        document.querySelectorAll(".a11y-img-placeholder").forEach(function (el) {
            el.remove();
        });
        document.querySelectorAll("img[data-a11y-hidden]").forEach(function (img) {
            img.removeAttribute("data-a11y-hidden");
            img.style.display = "";
        });

        if (!actif) return;

        document.querySelectorAll("img").forEach(function (img) {
            /* Ne pas toucher aux images déjà dans le modal accessibilité */
            if (img.closest("#modal_accessibilite")) return;

            /* Ne pas toucher aux images explicitement exclues */
            if (img.hasAttribute("data-a11y-keep")) return;

            img.setAttribute("data-a11y-hidden", "1");
            img.style.display = "none";

            var alt = (img.getAttribute("alt") || "").trim();
            if (alt) {
                /* Image informative : afficher le texte alt */
                var span = document.createElement("span");
                span.className = "a11y-img-placeholder";
                span.setAttribute("aria-label", alt);
                span.style.cssText = [
                    "display:inline-flex",
                    "align-items:center",
                    "justify-content:center",
                    "border:1px dashed #aaa",
                    "border-radius:4px",
                    "padding:4px 8px",
                    "font-size:.78rem",
                    "color:#666",
                    "background:#f8f8f8",
                    "max-width:100%",
                    "box-sizing:border-box",
                ].join(";");
                span.textContent = "[" + alt + "]";
                img.parentNode.insertBefore(span, img.nextSibling);
            }
            /* Images décoratives (alt="") : simplement masquées, rien à insérer */
        });
    }

    /* ------------------------------------------------------------------ */
    /* Application des préférences sur <body>                             */
    /* ------------------------------------------------------------------ */
    function appliquerPreferences(prefs) {
        var body = document.body;
        var html = document.documentElement;

        /* Contraste */
        body.classList.remove("a11y-contraste-eleve", "a11y-contraste-maximum");
        if (prefs.contraste === "eleve")   body.classList.add("a11y-contraste-eleve");
        if (prefs.contraste === "maximum") body.classList.add("a11y-contraste-maximum");

        /* Daltonisme */
        html.style.filter = (prefs.daltonisme && prefs.daltonisme !== "aucun")
            ? "url(#a11y-filter-" + prefs.daltonisme + ")"
            : "";

        /* Taille du texte */
        body.classList.remove("a11y-texte-petite", "a11y-texte-grande", "a11y-texte-tres-grande");
        if (prefs.taille_texte === "petite")      body.classList.add("a11y-texte-petite");
        if (prefs.taille_texte === "grande")      body.classList.add("a11y-texte-grande");
        if (prefs.taille_texte === "tres_grande") body.classList.add("a11y-texte-tres-grande");

        /* Souligner les liens */
        body.classList.toggle("a11y-souligner-liens", !!prefs.souligner_liens);

        /* Masquer les images */
        appliquerMasquerImages(!!prefs.masquer_images);

        /* Police dyslexie */
        body.classList.toggle("a11y-dyslexie", !!prefs.police_dyslexie);

        /* Espacement des lettres */
        body.classList.toggle("a11y-espacement", !!prefs.espacement_lettres);

        /* Interlignage */
        body.classList.remove("a11y-interlignage-augmente", "a11y-interlignage-large");
        if (prefs.interlignage === "augmente") body.classList.add("a11y-interlignage-augmente");
        if (prefs.interlignage === "large")    body.classList.add("a11y-interlignage-large");

        /* Masque de lecture */
        activerMasqueLecture(!!prefs.masque_lecture);

        /* Grandes zones de clic */
        body.classList.toggle("a11y-grandes-zones-clic", !!prefs.grandes_zones_clic);

        /* Agrandir le curseur */
        body.classList.remove("a11y-curseur-grand", "a11y-curseur-tres-grand");
        if (prefs.agrandir_curseur === "grand")      body.classList.add("a11y-curseur-grand");
        if (prefs.agrandir_curseur === "tres_grand") body.classList.add("a11y-curseur-tres-grand");

        /* Réduire les animations */
        body.classList.toggle("a11y-no-animations", !!prefs.reduire_animations);
    }

    /* ------------------------------------------------------------------ */
    /* Lecture du formulaire                                               */
    /* ------------------------------------------------------------------ */
    function lireFormulaire() {
        var f = document.getElementById("form_accessibilite");
        if (!f) return null;

        function sel(name) {
            var el = f.querySelector("select[name=" + name + "]");
            return el ? el.value : DEFAUTS[name];
        }
        function cb(name) {
            var el = f.querySelector("input[name=" + name + "]");
            return el ? el.checked : DEFAUTS[name];
        }

        return {
            contraste:          sel("contraste"),
            daltonisme:         sel("daltonisme"),
            taille_texte:       sel("taille_texte"),
            souligner_liens:    cb("souligner_liens"),
            masquer_images:     cb("masquer_images"),
            police_dyslexie:    cb("police_dyslexie"),
            espacement_lettres: cb("espacement_lettres"),
            interlignage:       sel("interlignage"),
            masque_lecture:     cb("masque_lecture"),
            grandes_zones_clic: cb("grandes_zones_clic"),
            agrandir_curseur:   sel("agrandir_curseur"),
            reduire_animations: cb("reduire_animations"),
        };
    }

    /* ------------------------------------------------------------------ */
    /* Synchronisation prefs → formulaire                                  */
    /* ------------------------------------------------------------------ */
    function prefsVersFormulaire(prefs) {
        var f = document.getElementById("form_accessibilite");
        if (!f) return;

        function setSelect(name, val) {
            var el = f.querySelector("select[name=" + name + "]");
            if (el) el.value = val;
        }
        function setCb(name, val) {
            var el = f.querySelector("input[name=" + name + "]");
            if (el) el.checked = !!val;
        }

        setSelect("contraste",          prefs.contraste);
        setSelect("daltonisme",         prefs.daltonisme);
        setSelect("taille_texte",       prefs.taille_texte);
        setCb("souligner_liens",        prefs.souligner_liens);
        setCb("masquer_images",         prefs.masquer_images);
        setCb("police_dyslexie",        prefs.police_dyslexie);
        setCb("espacement_lettres",     prefs.espacement_lettres);
        setSelect("interlignage",       prefs.interlignage);
        setCb("masque_lecture",         prefs.masque_lecture);
        setCb("grandes_zones_clic",     prefs.grandes_zones_clic);
        setSelect("agrandir_curseur",   prefs.agrandir_curseur);
        setCb("reduire_animations",     prefs.reduire_animations);
    }

    /* ------------------------------------------------------------------ */
    /* Gestionnaire central : change → lire → sauvegarder → appliquer    */
    /* ------------------------------------------------------------------ */
    function onChangement() {
        var prefs = lireFormulaire();
        if (!prefs) return;
        sauvegarderPreferences(prefs);
        appliquerPreferences(prefs);
        annoncerLecteurEcran("Réglage d'accessibilité mis à jour.");
    }

    /* ------------------------------------------------------------------ */
    /* Initialisation                                                      */
    /* ------------------------------------------------------------------ */
    document.addEventListener("DOMContentLoaded", function () {

        injecterFiltresSVG();

        /* Application immédiate des préférences sauvegardées */
        appliquerPreferences(lirePreferences());

        /* Pré-remplissage du formulaire à l'ouverture du modal */
        var modalEl = document.getElementById("modal_accessibilite");
        if (modalEl) {
            modalEl.addEventListener("show.bs.modal", function () {
                prefsVersFormulaire(lirePreferences());
            });
        }

        /* Écouteur temps réel unique sur le formulaire */
        var form = document.getElementById("form_accessibilite");
        if (form) {
            form.addEventListener("change", onChangement);
        }

        /* Bouton Réinitialiser */
        var btnReset = document.getElementById("btn_reinitialiser_accessibilite");
        if (btnReset) {
            btnReset.addEventListener("click", function () {
                try { localStorage.removeItem(CLE_STORAGE); } catch (e) {}
                appliquerPreferences(DEFAUTS);
                prefsVersFormulaire(DEFAUTS);
                annoncerLecteurEcran("Réglages d'accessibilité réinitialisés aux valeurs par défaut.");
                if (typeof toastr !== "undefined") {
                    toastr.info("Réglages d'accessibilité réinitialisés.");
                }
            });
        }

    });

}());
