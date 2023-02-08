function loadDataTableGames() {
        function renderUser(data) {
            var online_class = data.is_online ? 'online' : 'offline'
            var tooltip = ''
            if (data.kgs_data) {
                tooltip += '<p'
                if (data.kgs_online) {
                    tooltip += " class='online'"
                } else {
                    tooltip += " class='offline'"
                }
                tooltip += '>KGS: ' + data.kgs_data.username + ' ' + data.kgs_data.rank + '</p>'
            }
            if (data.ogs_data) {
                tooltip += '<p'
                if (data.ogs_online) {
                    tooltip += " class='online'"
                } else {
                    tooltip += " class='offline'"
                }
                tooltip += '>OGS: ' + data.ogs_data.username + ' ' + data.ogs_data.rank + '</p>'

            }
            if (data.discord_data) {
                tooltip += "<p class='" + data.discord_data.status + "'>Discord: "
                tooltip += data.discord_data.username + ' (' + data.discord_data.discriminator +')</p>'
            }
            var link = '<a href="' + data.account_url + '" class="' + online_class + '" '
                    + 'data-toggle="tooltip" data-html="true" rel="tooltip" title="' + tooltip + '" >' + data.username
            if (data.is_meijin) {
                link += ' <i class="fa fa-trophy"></i>'
            }
            link += '</a>'
            return link
        }
        game_table = $('#game-table')
        community_pk = game_table[0].getAttribute("data-community-pk")
        event_pk = game_table[0].getAttribute("data-event-pk")
        game_table.DataTable({
            "bLengthChange": false ,
            drawCallback: function () {
                $('#game-table_wrapper > div:first-child .col-sm-6:nth-child(1)').attr("class", 'col-sm-4');
                $('#game-table_wrapper > div:first-child .col-sm-6:nth-child(2)').attr('class', 'col-sm-8');
                $('#game-table_wrapper > div:last-child .col-sm-5:nth-child(1)').attr('class', 'row');
                $('#game-table_wrapper > div:last-child .col-sm-7:nth-child(2)').attr('class', 'row');
                $('#game-table_wrapper > div:last-child').css('margin', 0);
                $('#game-table_wrapper > div:last-child > .row').css('margin', 0);
                $("[data-toggle=tooltip]").tooltip();
            },
            "columnDefs": [
                {
                    targets: 0,
                    render: $.fn.dataTable.render.moment( 'YYYY-MM-DD','L', '{{LANGUAGE_CODE}}' )
                },
                {
                    targets: [1, 2],
                    render: function(data, type, row) {
                        return renderUser(data)
                    },
                },
                {
                    targets: 3,
                    render: function(data, type, row) {
                        return '<a role="button" onclick="load_game('
                                + data.sgf_pk + ')">' + data.sgf_result + '</a>'
                    },
                },
            ],
            "order": [[ 0, "desc" ]],
            "deferRender": true,
            "ajax": {
              "url": "/league/games-api/",
              "type": "GET",
              "data": function ( d ) {
                return $.extend( {}, d, {
                  "league": event_pk,
                    "community": community_pk
                } );
              }
            }
        });
    }