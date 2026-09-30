$('#searchfield-custom').on('input',()=>{
    $('#searchresults').show();
    $(".geoportail").remove();
})

var customUtils = (function () {

    const getRandomColor = ()=>{
        const str ='123456789ABCDEF';
        let color ='#';
        for (let i=0 ; i<6 ; i++){
            color += str[Math.floor(Math.random()*15)]
        }
        return color;
    }

    const validateFormOnInput = (form,btn)=>{
        $(`#${form} input, #${form} textarea,#${form} select`).on('input', function () {
            validate(form,btn)
        })
    }
    const validate=(form,btn)=> {
        let show = true;
        $(`#${form} input, #${form} select,#${form} textarea`).each(function () {
            if (($(this).val() == '' || !$(this).val()) && $(this).attr('required') == 'required') {
                show = false;
            }
        })
        if (show) {
            $(`#${btn}`).prop('disabled', false)
        } else $(`#${btn}`).prop('disabled', 'disabled')
    }
    const resetForm=(form)=>{
        $(`#${form} input, #${form} select,#${form} textarea`).each(function () {
            $(this).val('');
        })
    }
    const _toAst = (className, message, duration,position) => {
        const snackBar = document.getElementById("snackbar");
        snackBar.classList.add('show');
        snackBar.classList.add(className);
        position?snackBar.classList.add(position):snackBar.classList.add('bottom-center')
        snackBar.innerText = message
        setTimeout(() => {
            snackBar.classList.remove("show");
            snackBar.classList.remove(className);
            // if(position)
            // snackBar.classList.remove(position)
        }, duration)
    }


    const hasAnyRole=(roles)=>
    {
        var hasRole=false;
        var auths='auth' in sessionStorage && sessionStorage.getItem('auth')? sessionStorage.getItem('auth').split(','):[];

        auths.forEach(auth=>{
            if(roles.includes(auth)) {
                hasRole = true;
                return;
            };
        })
        return hasRole ;
    }

   const loadConfiguration=(e,eData,theme)=>{
        //get JSON conf from xml;
        var _conf = configuration.parseXML(eData.xml);
        listConf = _conf;

        var style = "css/themes/default.css";
        if (!theme && _conf.application.style && _conf.application.style.match("css")) {
            style = _conf.application.style;
        } else if (theme) {
            style = "css/themes/" + theme + ".css";
        }
        $('head').prepend('<link rel="stylesheet" href="' + style + '" type="text/css" />');
        var title = "";
        if (_conf.application.title) {
            title = _conf.application.title;
            $("#loader-subtitle").text(title);
        }
        configuration.load(_conf);
        $.each(listConf.extensions, function (i, ex) {
            ex.forEach(e => {
                $(`#${e.id}-extension-btn`).prop('disabled', false)
            })

        })

        setTimeout(function () {
            $("#loading-page").hide();
            $("#main").css("opacity", 1).hide();
            $("#main").fadeIn(1500);
            mviewer.getMap().updateSize();
            map = mviewer.getMap()
            // olCesium=new olcs.OLCesium({
            //     map:mviewer.getMap()
            // })
            // olCesium.setEnabled(false)
        }, 2000);
        $("#map").focus();
    }

    const getCoordinatesPoint=(geom)=>{
        var coordinates=[];
        switch (geom.type) {
            case 'Point':{coordinates=geom.coordinates};break;
            case 'MultiPoint':{coordinates=geom.coordinates[0]};break;
            default:break;
        }
        return coordinates;
    }

    /* this sestion is reserved to forms generic*/
    loadGroupForm = async (idType,entity) => {
        const response = await fetch(_conf._endPointApi+`/params/form-groups/${idType}/${entity}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        let res = await response.json()
        return res || []; //extract JSON from the http response
    }

    loadFieldsEvolution = async (idType)=>{
        const response = await fetch(_conf._endPointApi+`/params/form-evolution-event/${idType}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        let res = await response.json()
        return res || []; //extract JSON from the http response
    }
    addGroups=(idElementTab,idElementTabContent,groups)=>{
        groups.forEach(gr => {
            $(`#${idElementTab}`).append(`
                    <li role="presentation" class="${gr.id == 1 ? 'active' : ''}">
                                <a href="#groupe-${gr.id}" role="tab" data-toggle="tab">${gr.libelle}</a>
                            </li>
                `);

            $(`#${idElementTabContent}`).append(`
                            <div class="tab-pane ${gr.id == 1 ? 'active' : ''}" id="groupe-${gr.id}" role="tabpanel">
                            </div>
                `)
        })
    }
    convertToTime=( millisseconds)=>{
        let seconds = Math.floor(millisseconds/1000);
        let minutes= Math.floor(seconds/60);
        let hours = Math.floor(minutes/60);
        seconds = seconds % 60;
        minutes = minutes % 60;
        hours = hours % 24
        return `${getSecondDigit(hours)}:${getSecondDigit(minutes)}:${getSecondDigit(seconds)}`
    }
    getSecondDigit=(num)=>{
        return num.toString().padStart(2,'0')
    }

    getStatus= async (id_type)=>{
        const response = await fetch(_conf._endPointApi+`/params/all-status`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        let res = await response.json()
        return res || []; //extract JSON from the http response
    }
    getLayerById= async (idLayer)=>{
        const response = await fetch(`${_conf._endPointDataServer}/geodata/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=geodata:${idLayer}&outputFormat=application/json`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        let res = await response.json()
        return res || [];
    }

    return {
        toAst: _toAst,
        validateFormOnInput,
        resetForm,
        getRandomColor,
        validate,
        hasAnyRole,
        loadConfiguration,
        getCoordinatesPoint,
        loadGroupForm,
        addGroups,
        loadFieldsEvolution,
        convertToTime,
        getStatus,
        getLayerById
    };

})();