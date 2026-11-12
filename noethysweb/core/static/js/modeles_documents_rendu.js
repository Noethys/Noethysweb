/*
 *  Noethysweb - Rendu commun des modèles de documents (fabric.js 3.6)
 *  Utilisé par l'éditeur et par les aperçus de la liste des modèles.
 *  Distribué sous licence GNU GPL.
 *
 *  Unités : 1 unité = 1 mm.
 */

(function () {
    "use strict";

    // Textes : 1 point typographique en mm. Le PDF imprime fontSize en points ;
    // avec cette échelle, l'affichage correspond exactement à la taille imprimée.
    const ECHELLE_TEXTE = 25.4 / 72;
    const BLEU_SPECIAL = "#378ADD";

    // Interligne du PDF (1,2 x la taille), converti dans l'unité de fabric (qui multiplie par _fontSizeMult)
    function interligne_texte() {
        return 1.2 / fabric.Text.prototype._fontSizeMult;
    }

    function affecter(objet, proprietes) {
        if (typeof objet.set === "function") { objet.set(proprietes); } else { Object.assign(objet, proprietes); }
    }

    // Aligne l'affichage d'un texte (objet fabric ou JSON) sur le rendu PDF, sans rien changer à ce qui est imprimé :
    // échelle d'un point, largeur du cadre conservée en mm, interligne du PDF, justifié sans la dernière ligne.
    function aligner_texte_sur_pdf(objet) {
        if (!objet || objet.categorie !== "texte" || typeof objet.text !== "string") { return objet; }
        const proprietes = {lineHeight: interligne_texte()};
        const sx = objet.scaleX || 1;
        const sy = objet.scaleY || 1;
        if (Math.abs(sx - ECHELLE_TEXTE) > 1e-6 || Math.abs(sy - ECHELLE_TEXTE) > 1e-6) {
            proprietes.width = (objet.width || 0) * sx / ECHELLE_TEXTE;
            proprietes.scaleX = ECHELLE_TEXTE;
            proprietes.scaleY = ECHELLE_TEXTE;
        }
        // fabric justifie aussi la dernière ligne des paragraphes avec "justify" ; "justify-left" l'aligne à gauche comme le PDF
        if (objet.textAlign === "justify") { proprietes.textAlign = "justify-left"; }
        affecter(objet, proprietes);
        return objet;
    }

    // Cadres spéciaux (tableau des prestations, cadre principal...) : zone réservée remplie à l'impression.
    // Rendu d'affichage uniquement ; le même style est dessiné dans l'aperçu PDF (ObjetPDF.DessineCadreSpecial).
    // Avec objet.rendu_miniature = true : sans étiquette ni mention (miniatures de la liste).
    function dessiner_cadre_special(ctx) {
        const w = this.width;
        const h = this.height;
        const x = -w / 2;
        const y = -h / 2;
        const zoom = (this.canvas ? this.canvas.getZoom() : 1) * (this.scaleX || 1);
        const px = 1 / zoom; // un pixel écran, en mm
        const miniature = !!this.rendu_miniature;
        ctx.save();
        ctx.fillStyle = "rgba(55,138,221,0.06)";
        ctx.fillRect(x, y, w, h);
        ctx.strokeStyle = BLEU_SPECIAL;
        ctx.lineWidth = px;
        ctx.setLineDash(miniature ? [2 * px, 2 * px] : [4 * px, 3 * px]);
        ctx.strokeRect(x + px / 2, y + px / 2, w - px, h - px);
        ctx.setLineDash([]);

        // Étiquette (taille constante à l'écran)
        const taille = 11 * px;
        const marge = 6 * px;
        const icone = 10 * px;
        const haut_etiquette = taille + 8 * px;

        // Aperçu des lignes du tableau (en mm, comme dans le PDF)
        const largeurs = [1, 0.92, 0.85, 0.95];
        let ligne_y = y + (miniature ? 4.5 : Math.max(haut_etiquette, 4.5)) + 3;
        for (let i = 0; i < 8 && ligne_y + 2 < y + h - 6; i++) {
            ctx.fillStyle = i === 0 ? "rgba(55,138,221,0.22)" : "rgba(55,138,221,0.12)";
            ctx.fillRect(x + 3, ligne_y, (w - 6) * largeurs[i % 4], 2);
            ligne_y += 5;
        }

        if (!miniature) {
            ctx.font = taille + "px sans-serif";
            const libelle = this.nom || "Zone spéciale";
            const largeur_etiquette = Math.min(ctx.measureText(libelle).width + 3 * marge + icone, w);
            ctx.fillStyle = BLEU_SPECIAL;
            ctx.fillRect(x, y, largeur_etiquette, haut_etiquette);
            ctx.save();
            ctx.beginPath();
            ctx.rect(x, y, largeur_etiquette, haut_etiquette);
            ctx.clip();
            // Icône "tableau"
            ctx.strokeStyle = "#ffffff";
            ctx.lineWidth = px;
            const ix = x + marge;
            const iy = y + (haut_etiquette - icone * 0.8) / 2;
            ctx.strokeRect(ix, iy, icone, icone * 0.8);
            ctx.beginPath();
            ctx.moveTo(ix, iy + icone * 0.3); ctx.lineTo(ix + icone, iy + icone * 0.3);
            ctx.moveTo(ix + icone * 0.4, iy); ctx.lineTo(ix + icone * 0.4, iy + icone * 0.8);
            ctx.stroke();
            ctx.fillStyle = "#ffffff";
            ctx.textBaseline = "middle";
            ctx.fillText(libelle, ix + icone + marge * 0.8, y + haut_etiquette / 2 + px);
            ctx.restore();

            // Mention en pied de cadre
            if (h * zoom > 60) {
                ctx.font = (9 * px) + "px sans-serif";
                ctx.fillStyle = "#185FA5";
                ctx.textAlign = "right";
                ctx.textBaseline = "bottom";
                ctx.fillText("rempli à l'impression", x + w - marge, y + h - 4 * px);
            }
        }
        ctx.restore();
    }

    function preparer_cadre_special(objet) {
        if (!objet || objet.categorie !== "special") { return; }
        objet._render = dessiner_cadre_special;
        objet.objectCaching = false;
    }

    function est_datamatrix(objet) {
        return !!objet && objet.categorie === "barcode" && objet.cb_norme === "datamatrix";
    }

    // Remplace l'image d'un objet fabric en conservant sa taille affichée (en mm), puis appelle callback
    function remplacer_image(objet, url, callback) {
        const largeur = objet.width * objet.scaleX;
        const hauteur = objet.height * objet.scaleY;
        objet.setSrc(url, function (img) {
            const element = img && img.getElement ? img.getElement() : null;
            const nw = element ? (element.naturalWidth || element.width) : 0;
            const nh = element ? (element.naturalHeight || element.height) : 0;
            if (nw && nh) {
                img.set({width: nw, height: nh, cropX: 0, cropY: 0, scaleX: largeur / nw, scaleY: hauteur / nh});
                img.setCoords();
            }
            if (callback) { callback(img); }
        });
    }

    window.RenduModelesDocuments = {
        ECHELLE_TEXTE: ECHELLE_TEXTE,
        interligne_texte: interligne_texte,
        aligner_texte_sur_pdf: aligner_texte_sur_pdf,
        dessiner_cadre_special: dessiner_cadre_special,
        preparer_cadre_special: preparer_cadre_special,
        est_datamatrix: est_datamatrix,
        remplacer_image: remplacer_image,
    };
})();
