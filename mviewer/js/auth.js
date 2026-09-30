

isAuthenticated = (prop) => {

    if ("auth" in sessionStorage && sessionStorage.getItem('auth')) {
        sessionStorage.getItem('auth').split(',').map(s => {
            $(`.${s}`).css('display', prop)
        })
    }

}
isAuthenticated('block');
if ("isConnected" in sessionStorage && sessionStorage.getItem('isConnected') == "yes") {
    $('#wrapper').css('display', 'block')
    $('.navbar').css('display', 'block')
    $('.login').css('display', 'none')
}

if ("firstname" in sessionStorage && "lastname" in sessionStorage) {
    $("#auth_connected_user").text(sessionStorage.getItem('firtsname') + ' ' + sessionStorage.getItem('lastname'))
}


const connect = () => {
    getUserByLogin($("#username").val()).then(res => {
        if (res[0] && CryptoJS.AES.decrypt(res[0].password, 'secret key 123').toString(CryptoJS.enc.Utf8) == $("#password").val()) {
            if (res[0].isActive == true) {
                getAuthoritiesUser([res[0].id]).then(auth => {
                    /* display element by auth of user */
                    const auths = auth.map(a => {
                        $(`.${a.libelle}`).css('display', "block")
                        return a.libelle;
                    })
                    sessionStorage.setItem('id',res[0].id)
                    sessionStorage.setItem('login', res[0].login)
                    sessionStorage.setItem('auth', auths)
                    sessionStorage.removeItem('isConnected')
                    sessionStorage.setItem('isConnected', 'yes')
                    sessionStorage.setItem('firtsname', res[0].first_name)
                    sessionStorage.setItem('lastname', res[0].last_name)
                    window.top.location.reload(true)
                    // $('#wrapper').css('display', 'block')
                    // $('.navbar').css('display', 'block')
                    // $('.login').css('display', 'none')
                    mviewer.getMap().updateSize();
                    mviewer.toggleLegend();
                    $("#auth_connected_user").text(sessionStorage.getItem('firtsname') + ' ' + sessionStorage.getItem('lastname'))
                })
            } else {
                $('.alert-login-actif').css('display', 'block')
                $('.alert-login').css('display', 'none')
            }

        } else {
            $('.alert-login').css('display', 'block')
            $('.alert-login-actif').css('display', 'none')
        }
    })

}

const deconnect = () => {
    isAuthenticated('none')
    sessionStorage.removeItem('isConnected')
    sessionStorage.removeItem('firtsname')
    sessionStorage.removeItem('lastname')
    sessionStorage.removeItem('auth')
    sessionStorage.removeItem('login')
    sessionStorage.removeItem('id')
    window.top.location.reload(true);
    window.history.forward(1)

}
setTimeout(()=>{
    deconnect()
},12*60*60*1000)
// to switch from signin panel to signup pane or else

const onSwitch = (classToremove, classToadd) => {
    $(".login_inp_password_comf_error").css('display', 'none')
    $(".alert-login-creation-error").css('display', 'none')
    $(".alert-login-creation-succes").css('display', 'none')

    $('.signup-form input').each(function () {
        if ($(this).prop('type') != 'button')
            $(this).val('')
    })
    $(classToremove).removeClass('switched');
    $(classToadd).addClass('switched');
}

//zb_a : get user by login from database

const getUserByLogin = async (username) => {
    const response = await fetch(_conf._endPointApi+'/users/' + username, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    let res = await response.json()
    return res || []; //extract JSON from the http response
}

// zb_a : retrieve all roles of connected user
const getAuthoritiesUser = async (idUser) => {
    const response = await fetch(_conf._endPointApi+'/users/authorities/' + idUser, {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json'
        }
    });
    let res = await response.json()
    return res || []; //extract JSON from the http response
}

// zb_a : validation form

function validate(form, btn) {
    let show = true;
    $(form + ' input').each(function () {
        if ($(this).val() == '' && $(this).attr('required') == 'required') {
            show = false;
        }
    })
    if (show) {
        $(btn).prop('disabled', false)
    } else $(btn).prop('disabled', 'disabled')

}

$('.auth-modal-form input').on('input', function () {
    validate('.auth-modal-form', '#btn-update-password')
});

$('.signup-form input').on('input', function () {
    validate('.signup-form', '#btn-signup')
})


// zb_a : method to sign up
signup = () => {
    if ($('#login_inp_password').val() == $('#login_inp_password_comf').val()) {
        $(".login_inp_password_comf_error").css('display', 'none')
        getUserByLogin($("#login_inp_login").val()).then(res => {
            if (res[0]) {
                $(".alert-login-exist").css("display", 'block')
            } else {
                $(".alert-login-exist").css("display", 'none')
                createUser();
            }
        })

    } else {
        $(".login_inp_password_comf_error").css('display', 'block')
    }
}
// zb_a : create user

createUser = function () {
    fetch(_conf._endPointApi+'/users/create',
        {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                login: $('#login_inp_login').val(),
                first_name: $('#login_inp_nom').val(),
                last_name: $('#login_inp_prenom').val(),
                password: CryptoJS.AES.encrypt($('#login_inp_password').val(), 'secret key 123').toString()

            })
        })
        .then(response => {
            if (response.ok) {
                $('.signup-form input').each(function () {
                    if ($('#btn-signup').prop('type') != 'button')
                        $(this).val('')
                })
                $(".alert-login-creation-succes").css("display", 'block')
                return response.text();
            } else {
                $(".alert-login-creation-error").css("display", 'block')

            }
        }).then(data => {})
        .catch(reason => console.log(reason))
}
newPassword = function (password,login) {
    fetch(_conf._endPointApi+'/users/password/edit',
        {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                login,
                password: CryptoJS.AES.encrypt(password, 'secret key 123').toString()
            })
        })
        .then(response => {
            if (response.ok) {
                return response.text();
            } else {
                $(".alert-login-creation-error").css("display", 'block')
            }
        }).then(data => {
        customUtils.toAst("success",'Votre mot de passe a été modifié avec succès',3000);
        $('#panel-update-password').modal('hide');
    })
        .catch(reason => console.log(reason))
}

updatePassword = () => {

    if ($('#new-password').val() == $('#confirmation-new-password').val()) {
        getUserByLogin(sessionStorage.getItem('login')).then(res => {
            if ( CryptoJS.AES.decrypt(res[0].password, 'secret key 123').toString(CryptoJS.enc.Utf8) == $('#old-password').val() ) {
                newPassword($('#new-password').val(),sessionStorage.getItem('login'));
                $(".new-password-comf-error").hide();
            } else {
                $(".old-password-error").show();
                $(".new-password-comf-error").hide();
            }
            setTimeout(()=>{
                $(".new-password-comf-error").hide();
                $(".old-password-error").hide();
            },3000)
        })

    } else {
        $(".new-password-comf-error").show();
    }
}


