$(document).ready(function() {

    // using jQuery
    var csrftoken = jQuery("[name=csrfmiddlewaretoken]").val();

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    // set csrf header
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });


    var opts = {
        bProcessing: true,
        sPaginationType: "full_numbers",
        bDeferRender: true,
        // stateSave: true,
        responsive: false,
        rowReorder: active_deplacements,
        rowGroup: colonne_regroupement,
        lengthMenu: [
            [ 10, 25, 50, 100, 200, -1 ],
            [ '10 lignes', '25 lignes', '50 lignes', '100 lignes', '200 lignes', 'Tout afficher' ]
        ],
        // dom: "<'pull-right'B><'pull-right'f><'table-scrollable't><'pull-left'i><'pull-right'p>",
        // dom: '<"dt-buttons-haut"<\'pull-right\'B><\'pull-right\'f><\'table-scrollable\'t>><\'pull-left\'i><\'pull-right\'p>',
        // dom: '<"top"<\'pull-left\'i><\'pull-right\'B>>rt<"bottom"<\'pull-left\'f>lp>',
        // dom: "<'row'<'col-sm-6'i><'col-sm-6'<\"dt-buttons-haut\"B>>>" +
        //     "<'row'<'col-sm-12'tr>>" +
        //     "<'row'<'col-sm-2'f><'col-sm-10'p>>",
        dom: "<'barre_menu_dt_gauche'> <'d-flex flex-wrap justify-content-end dt-buttons-haut'<f><B>>" +
        "<'row'<'col-sm-12'tr>>" +
        "<'d-flex flex-wrap justify-content-between'<i><p>>",

        buttons:[
            {
                text: '<i class="fa fa-filter" title="Ajouter un filtre"></i>',
                action: function (e, dt, node, config) {
                    ajouter_filtre();
                },
                className: "btn-default"
            },
            {
                text: '<i class="fa fa-refresh" title="Actualiser"></i>',
                action: function (e, dt, node, config) {
                    dt.ajax.reload();
                },
                className: "btn-default"
            },
            {
                extend: 'print',
                text: '<i class="fa fa-print" title="Imprimer"></i>',
                title: impression_titre,
                messageTop: impression_introduction,
                messageBottom: impression_conclusion,
                autoPrint: true,
                className: "btn-default",
                customize: function ( win ) {
                    $(win.document.body)
                        .css( 'font-size', '7pt' )
                        ;
                    $(win.document.body).find( 'table' )
                        .css( 'font-size', 'inherit' )
                        .css( 'border-collapse', 'collapse' )
                        .css( 'border', '1px solid black' )
                    ;
                    $(win.document.body).find('td').css( 'border', '1px solid black' );
                    // $(win.document.body).find('th').css( 'border', '1px solid black' );
                    // $(win.document.body).find('th').addClass('display').css('text-align', 'center');
                    // $(win.document.body).find('table').addClass('display').css('text-align', 'center');
                    // $(win.document.body).find('tr:nth-child(odd) td').each(function (index) {
                    //     $(this).css('background-color', '#D0D0D0');
                    // });
                    $(win.document.body).find('h1').css('text-align','center');
                    }
            },
            {
                extend: 'collection',
                text: '<i class="fa fa-share-square-o" title="Exporter"></i>',
                className: "btn-default",
                buttons: [
                    'copy',
                    'csv',
                    'excel',
                    {
                        text: 'PDF (portrait)',
                        extend: 'pdf',
                        orientation: 'portrait',
                    },
                    {
                        text: 'PDF (paysage)',
                        extend: 'pdf',
                        orientation: 'landscape',
                    }
                ]
            },
            {
                extend: 'colvis',
                text: '<i class="fa fa-eye-slash" title="Afficher ou masquer des colonnes"></i>',
                className: "btn-default",
            },
            // {
            //     extend: 'collection',
            //     text: '<i class="fa fa-check-square-o" title="Cocher ou décocher"></i>',
            //     className: "btn-default",
            //     buttons: [
            //         'selectAll',
            //         'selectNone',
            //     ]
            // },
            {
                extend: 'pageLength',
                text: '<i class="fa fa-cog" title="Configuration"></i>',
                className: "btn-default",
            },

        ],
        footerCallback: function ( row, data, start, end, display ) {
            var api = this.api();
            nb_cols = api.columns().nodes().length;
            var j = 1;
            while(j < nb_cols){
                var pageTotal = api
                    .column( j, { page: 'current'} )
                    .data()
                    .reduce( function (a, b) {
                return Number(a) + Number(b);
            }, 0 );
          // Update footer
          $( api.column( j ).footer() ).html(pageTotal);
            j++;
        }},
        language: {
            buttons: {
                colvis: "Colonnes",
                copy: "Copier",
                selectAll: "Tout sélectionner",
                selectNone: "Tout déselectionner"
            },
            processing:     "Traitement en cours...",
            search:         "",
            lengthMenu:     "Afficher _MENU_ &eacute;l&eacute;ments",
            info:           "Affichage de l'élément _START_ &agrave; _END_ sur _TOTAL_ éléments",
            infoEmpty:      "Affichage de l'élément 0 &agrave; 0 sur 0 éléments",
            infoFiltered:   "(filtr&eacute; de _MAX_ éléments au total)",
            infoPostFix:    "",
            loadingRecords: "Chargement en cours...",
            zeroRecords:    "Aucun &eacute;l&eacute;ment &agrave; afficher",
            emptyTable:     "Aucune donnée",
            paginate: {
                first:      "Premier",
                previous:   "Pr&eacute;c&eacute;dent",
                next:       "Suivant",
                last:       "Dernier"
            },
            aria: {
                sortAscending:  ": activer pour trier la colonne par ordre croissant",
                sortDescending: ": activer pour trier la colonne par ordre décroissant"
            },
            select: {
                "rows": {
                    "_": "%d lignes sélectionnées",
                    "0": "",
                    "1": "1 ligne sélectionnée"
                }
            },
        },
        fixedHeader: {
            header: true,
            footer: true
        },
    };

    // Checkbox colonne
    if (active_checkbox === true) {
        opts['columnDefs'] = [{orderable: false, className: 'select-checkbox', targets: 0}];
        opts['select'] = {style: 'multi', selector: 'td:first-child'};
    };

    if (hauteur_table != '') {
        jQuery.extend(opts, {"scrollY": hauteur_table, "scrollCollapse": true, "paging": false});
    };

    var datatable = datatableview.initialize($('.datatable'), opts);
    var table = datatable.api;

    // Initialisation des custom-datatable
    opts["pageLength"] = 25;
    $('.custom-datatable').DataTable(opts);

    // Déplacement d'une ligne
    var table = $('.datatable').DataTable()
    table.on('row-reordered', function (e, diff, edit) {
        var deplacements = {};
        for ( var i=0, ien=diff.length ; i<ien ; i++ ) {
            var rowData = table.row( diff[i].node ).data();
            deplacements[rowData["DT_RowId"]] = diff[i].newPosition + 1;
        }
        console.log("deplacements=", deplacements)
        $.ajax({
            type: "POST",
            url: "deplacer_lignes",
            data: {"deplacements": JSON.stringify(deplacements),},
            datatype: "json",
            success: function (data) {
                var index_page = table.page();
                table.ajax.reload();
                table.page(index_page).draw('page');
            }
        });
    });

    $('.datatable').on('init.dt', function () {
        if (liste_coches.length > 0) {
            var table = $('.datatable').DataTable();
            $.each(table.rows().data(), function (index, valeurs) {
                if (jQuery.inArray(parseInt(valeurs[1]), liste_coches) > -1) {
                    table.row(":eq(" + index + ")", {page: "current"}).select();
                };
            });
        };
    });


/*
    $('.datatable').on( 'select.dt deselect.dt',  function (evtObj) {
        var all = table.rows().nodes().length;
        var sel = table.rows(".selected").nodes().length;

        console.log(all, sel);

        if(all === sel){

          $(".toggle-all").closest("tr").addClass("selected");
        }
        else{

          $(".toggle-all").closest("tr").removeClass("selected");
        }
    });

    $('.datatable').on('click', '.toggle-all', function() {
        $(this).closest("tr").toggleClass("selected");
        if($(this).closest("tr").hasClass("selected")){
            table.rows().select();
        }
        else {
            table.rows().deselect();
        }
    });
*/


    $('.dataTables_filter input[type="search"]').
        attr('placeholder', 'Rechercher...').
        css({'width':'100px', 'height':'35px', 'margin-top':'2px', 'margin-left':'0px'});


    // On check colonne du header
    $("#checkbox_all").on("change", function(){
        if ($("#checkbox_all").prop("checked")) {
            $('.datatable').DataTable().rows().select();
        } else {
            $('.datatable').DataTable().rows().deselect();
        };
    });


    // Si coche ou décoche ligne
    $('.datatable').on('select.dt deselect.dt',  function (evtObj) {
        if(bouton_supprimer) {
            var bouton = "<button id='bouton_supprimer_plusieurs' class='btn btn-danger pull-left' onclick='supprimer_selections()' title='Supprimer les lignes sélectionnées' tabindex='0' aria-controls='DataTables_Table_0' type='button'><span><i class='fa fa-level-down fa-flip-horizontal margin-r-5'></i> Supprimer</span></button>"
            if (!($("#bouton_supprimer_plusieurs").length) && (table.rows(".selected").nodes().length)) {$(".barre_menu_dt_gauche").append(bouton)};
            if (($("#bouton_supprimer_plusieurs").length) && !(table.rows(".selected").nodes().length)) {$("#bouton_supprimer_plusieurs").remove()};
        }
    });



});

function get_coches() {
    // var table = $('.datatable').DataTable();
    var table = new $.fn.dataTable.Api('.datatable');
    var lignes = table.rows({selected: true});
    var data = lignes.data().toArray();
    // Récupère la liste des ids des lignes sélectionnées
    var listepk = [];
    $.each(data, function(index, valeurs) {
        listepk.push(parseInt(valeurs[1]));
    });
    return listepk;
}

function supprimer_selections() {
    var listepk = get_coches();
    var url = url_supprimer_plusieurs.replace("xxx", listepk.join(";"));
    window.location = url;
}
