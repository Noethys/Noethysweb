(function () {

    "use strict";


    const ETATS = {
        reservation: {
            label: "À pointer",
            classe: "reservation"
        },

        present: {
            label: "Présent",
            classe: "present"
        },

        absentj: {
            label: "Absent justifié",
            classe: "absentj"
        },

        absenti: {
            label: "Absent injustifié",
            classe: "absenti"
        },

        attente: {
            label: "Attente",
            classe: "attente"
        },

        refus: {
            label: "Refus",
            classe: "refus"
        },

        demande: {
            label: "Demande",
            classe: "demande"
        }
    };


    let afficherSeulementReservations = false;


    function getCasesConsommation() {

        const resultat = [];

        /*
         * Certaines cases du gestionnaire sont des parents techniques
         * (événements, multihoraires...).
         *
         * On ne conserve ici que les cases ayant réellement
         * une consommation.
         */

        Object.keys(dict_cases).forEach(function (key) {

            const caseTableau = dict_cases[key];

            if (!caseTableau) {
                return;
            }

            if (!caseTableau.consommations) {
                return;
            }

            if (caseTableau.consommations.length === 0) {
                return;
            }

            /*
             * Une case enfant événement/multi peut pointer sur la même
             * consommation que sa case parent.
             *
             * On éliminera ensuite les doublons par ID consommation.
             */

            resultat.push(caseTableau);

        });

        return resultat;
    }


function construireDonnees() {

    const individus = {};

    Object.entries(window.emargementIndividus).forEach(
        function ([inscription, personne]) {

            individus[inscription] = {
                inscription: inscription,
                individu: personne.id,
                nom: personne.nom,
                prenom: personne.prenom,
                cases: []
            };

        }
    );


    /*
     * Si des cases existent, on les rattache.
     */
    if (
        typeof dict_cases !== "undefined" &&
        Object.keys(dict_cases).length > 0
    ) {

        Object.keys(dict_cases).forEach(function (key) {

            const caseTableau = dict_cases[key];

            if (
                !caseTableau ||
                !caseTableau.consommations ||
                caseTableau.consommations.length === 0
            ) {
                return;
            }

            const inscription =
                String(caseTableau.inscription);

            if (individus[inscription]) {
                individus[inscription].cases.push(caseTableau);
            }

        });

    }


    return Object.values(individus).sort(function (a, b) {

        return (
            (a.nom + " " + a.prenom)
                .localeCompare(
                    b.nom + " " + b.prenom,
                    "fr"
                )
        );

    });
}





    function labelUnite(caseTableau) {

        if (
            typeof dict_unites !== "undefined" &&
            dict_unites[caseTableau.unite]
        ) {

            return dict_unites[caseTableau.unite].nom;

        }

        return "Consommation";
    }


    function boutonEtat(caseTableau, etat, texte) {

        const conso = caseTableau.consommations[0];

        const actif =
            conso.etat === etat ? " actif" : "";

        return `
            <button
                type="button"
                class="emargement-etat ${etat}${actif}"
                data-case="${caseTableau.key}"
                data-etat="${etat}"
            >
                ${texte}
            </button>
        `;
    }


    function creerConsommation(caseTableau) {

        const conso = caseTableau.consommations[0];

        const etat =
            ETATS[conso.etat] || {
                label: conso.etat,
                classe: ""
            };


        return `
            <div class="emargement-consommation"
                 data-etat="${conso.etat}">

                <div class="emargement-unite">

                    <strong>
                        ${escapeHtml(labelUnite(caseTableau))}
                    </strong>

                    <span class="emargement-badge ${etat.classe}">
                        ${etat.label}
                    </span>

                </div>


                <div class="emargement-boutons">

                    ${boutonEtat(
                        caseTableau,
                        "present",
                        '<i class="fa fa-check"></i> Présent'
                    )}

                    ${boutonEtat(
                        caseTableau,
                        "absentj",
                        '<i class="fa fa-times"></i> Absent justifié'
                    )}

                    ${boutonEtat(
                        caseTableau,
                        "absenti",
                        '<i class="fa fa-times"></i> Absent'
                    )}

                    ${boutonEtat(
                        caseTableau,
                        "reservation",
                        '<i class="fa fa-undo"></i>'
                    )}

                </div>

            </div>
        `;
    }

function creerIndividu(individu) {

    let consommations;

    if (individu.cases.length > 0) {

        consommations =
            individu.cases
                .map(creerConsommation)
                .join("");

    } else {

        consommations = `
            <div class="emargement-consommation">

                <div class="emargement-unite">
                    <strong>Présence</strong>

                    <span class="emargement-badge reservation">
                        Non pointé
                    </span>
                </div>

                <div class="emargement-boutons">

                    <button
                        type="button"
                        class="emargement-nouvelle-conso present"
                        data-inscription="${individu.inscription}"
                        data-etat="present"
                    >
                        <i class="fa fa-check"></i>
                        Présent
                    </button>

                    <button
                        type="button"
                        class="emargement-nouvelle-conso absentj"
                        data-inscription="${individu.inscription}"
                        data-etat="absentj"
                    >
                        Absent justifié
                    </button>

                    <button
                        type="button"
                        class="emargement-nouvelle-conso absenti"
                        data-inscription="${individu.inscription}"
                        data-etat="absenti"
                    >
                        Absent
                    </button>

                </div>

            </div>
        `;
    }


    return `
        <div
            class="emargement-individu"
            data-inscription="${individu.inscription}"
            data-recherche="${escapeHtml(
                (
                    individu.nom +
                    " " +
                    individu.prenom
                ).toLocaleLowerCase("fr")
            )}"
        >

            <div class="emargement-identite">

                <div class="emargement-avatar">
                    ${escapeHtml(
                        (
                            individu.prenom ||
                            individu.nom ||
                            "?"
                        ).substring(0, 1).toUpperCase()
                    )}
                </div>

                <div class="emargement-nom">
                    ${escapeHtml(individu.nom)}
                    ${escapeHtml(individu.prenom)}
                </div>

            </div>

            <div class="emargement-consommations">
                ${consommations}
            </div>

        </div>
    `;
}



    function rafraichir() {

        const individus = construireDonnees();

        const html =
            individus.map(creerIndividu).join("");

        $("#emargement-liste").html(html);

        appliquerFiltres();

        mettreAJourResume();

    }


    function changerEtat(caseKey, etat) {

        if (!(caseKey in dict_cases)) {
            return;
        }

        const caseTableau = dict_cases[caseKey];

        /*
         * IMPORTANT :
         *
         * On passe volontairement par set_etat().
         * Ne surtout pas faire :
         *
         * caseTableau.consommations[0].etat = etat;
         *
         * car set_etat() déclenche également le recalcul
         * de facturation de Noethysweb.
         */

        const resultat =
            caseTableau.set_etat(etat);

        if (resultat !== false) {
            rafraichir();
        }

    }


    function trouverCasePourInscription(inscription) {

        if (typeof dict_cases === "undefined") {
            return null;
        }

        const idInscription = parseInt(inscription, 10);
        const candidates = Object.values(dict_cases).filter(function (caseTableau) {
            return caseTableau && caseTableau.inscription === idInscription;
        });

        if (candidates.length === 0) {
            return null;
        }

        // Priorité à une unité visible. Sur les activités simples il n'y en a
        // généralement qu'une ; cela évite de dépendre de l'ordre du dict.
        const visible = candidates.find(function (caseTableau) {
            return dict_unites[caseTableau.unite] !== undefined;
        });

        return visible || candidates[0];
    }


    function creerEtPointer(inscription, etat) {

        const caseTableau = trouverCasePourInscription(inscription);

        if (!caseTableau) {
            toastr.error(
                "Aucune unité ouverte n'est disponible pour cette inscription aujourd'hui."
            );
            return;
        }

        if (caseTableau.has_conso && caseTableau.has_conso()) {
            caseTableau.set_etat(etat);
        } else {
            caseTableau.creer_conso({etat: etat});
        }

        // creer_conso/set_etat mettent à jour le moteur de grille immédiatement.
        // La facturation, elle, est enregistrée par le mécanisme AJAX natif.
        rafraichir();
    }


    function tousPresents() {

        const casesAModifier = [];

        getCasesConsommation().forEach(function (caseTableau) {

            const conso =
                caseTableau.consommations[0];

            if (conso.etat === "reservation") {
                casesAModifier.push(caseTableau);
            }

        });


        if (casesAModifier.length === 0) {

            toastr.info(
                "Il n'y a aucune réservation restant à pointer."
            );

            return;

        }


        bootbox.confirm({

            title: "Valider les présences",

            message:
                "Marquer les " +
                casesAModifier.length +
                " réservation(s) restantes comme présentes ?",

            buttons: {

                confirm: {
                    label: "Oui, tous présents",
                    className: "btn-success"
                },

                cancel: {
                    label: "Annuler",
                    className: "btn-secondary"
                }

            },

            callback: function (confirmation) {

                if (!confirmation) {
                    return;
                }

                /*
                 * C'est exactement le principe déjà utilisé par
                 * le pointage par lot officiel de Noethysweb :
                 * une modification par case.
                 */

                casesAModifier.forEach(
                    function (caseTableau) {

                        caseTableau.set_etat("present");

                    }
                );

                rafraichir();

            }

        });

    }


    function mettreAJourResume() {

        let reservations = 0;
        let presents = 0;
        let absents = 0;
        let total = 0;


        getCasesConsommation().forEach(function (caseTableau) {

            const conso =
                caseTableau.consommations[0];

            total++;

            if (conso.etat === "reservation") {
                reservations++;
            }

            if (conso.etat === "present") {
                presents++;
            }

            if (
                conso.etat === "absentj" ||
                conso.etat === "absenti"
            ) {
                absents++;
            }

        });


        $("#emargement-resume").html(`
            <strong>${reservations}</strong> à pointer
            &nbsp;·&nbsp;
            <strong>${presents}</strong> présents
            &nbsp;·&nbsp;
            <strong>${absents}</strong> absents
            &nbsp;·&nbsp;
            ${total} consommations
        `);

    }


    function appliquerFiltres() {

        const recherche =
            $("#emargement-recherche")
                .val()
                .trim()
                .toLocaleLowerCase("fr");


        let nbreVisible = 0;


        $(".emargement-individu").each(function () {

            const element = $(this);

            let visible = true;


            if (recherche) {

                visible =
                    element
                        .data("recherche")
                        .includes(recherche);

            }


            if (
                visible &&
                afficherSeulementReservations
            ) {

                visible =
                    element
                        .find(
                            ".emargement-consommation" +
                            '[data-etat="reservation"]'
                        )
                        .length > 0;

            }


            element.toggle(visible);

            if (visible) {
                nbreVisible++;
            }

        });


        $("#emargement-vide").toggle(
            nbreVisible === 0
        );

    }


    function escapeHtml(texte) {

        return $("<div>")
            .text(texte || "")
            .html();

    }


    /*
     * Les événements sont délégués car la liste
     * est reconstruite après chaque pointage.
     */

    $(document).on(
        "click",
        ".emargement-etat",
        function () {

            changerEtat(
                $(this).data("case"),
                $(this).data("etat")
            );

        }
    );


    $(document).on(
        "click",
        ".emargement-nouvelle-conso",
        function () {
            creerEtPointer(
                $(this).data("inscription"),
                $(this).data("etat")
            );
        }
    );


    $(document).on(
        "click",
        "#emargement-tous-presents",
        tousPresents
    );


    $(document).on(
        "input",
        "#emargement-recherche",
        appliquerFiltres
    );


    $(document).on(
        "click",
        "#emargement-afficher-reservations",
        function () {

            afficherSeulementReservations =
                !afficherSeulementReservations;

            $(this).toggleClass(
                "btn-warning",
                afficherSeulementReservations
            );

            $(this).toggleClass(
                "btn-secondary",
                !afficherSeulementReservations
            );

            appliquerFiltres();

        }
    );


    /*
     * Le script est chargé avec defer : au DOMContentLoaded, la grille cachée
     * a déjà créé les Case_* disponibles. L'affichage de l'émargement ne doit
     * toutefois jamais dépendre de la présence de consommations : la liste des
     * inscrits vient de window.emargementIndividus.
     */
    $(document).ready(function () {
        rafraichir();
    });

})();
