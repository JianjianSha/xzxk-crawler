"use strict";
Object.defineProperty(exports, "__esModule", { value: true });

const jsdom = require("/home/jian/sha/src/python/crawler/administration/node_modules/jsdom");

const fs = require("fs")
// const axios = require("axios");

// for the sake of executed in PyExecjs environment, all non-standard module are loaded in form of file stream directly to method 'execjs.compile'
const { random, cipherText, DES3 } = require('./Decrypt.js');

function get_cookies_1() {
    const cookieJar = new jsdom.CookieJar();
    let options = {
        url: "http://wenshu.court.gov.cn/",
        runScripts: 'dangerously',
        cookieJar: cookieJar
    };

    let dom = new jsdom.JSDOM(``, options);
    dom.window.close();

    let cookie = '';
    cookieJar.getCookieString('http://wenshu.court.gov.cn/', (err, cookies) => {
        // if (err) {
        //     console.log(err);
        // }
        cookie = cookies;
    });
    return cookie;
}

async function get_cookies_async() {
    let indexUrl = 'http://wenshu.court.gov.cn/';
    const cookieJar = new jsdom.CookieJar();
    let options = {
        runScripts: 'dangerously',
        cookieJar: cookieJar
    };

    // async
    let dom = await jsdom.JSDOM.fromURL(indexUrl, options);
    dom.window.close();
    // let HM4hUBT0dDOn80S = cookieJar.store.idx['wenshu.court.gov.cn']['/']['HM4hUBT0dDOn80S'].value;
    // let HM4hUBT0dDOn80T = cookieJar.store.idx['wenshu.court.gov.cn']['/']['HM4hUBT0dDOn80T'].value;
    let cookie = '';
    cookieJar.getCookieString('http://wenshu.court.gov.cn/', (err, cookies) => {
        // if (err) {
        //     console.log(err);
        // }
        cookie = cookies;
    });
    return cookie;
    // if (!cookie.includes('HM4hUBT0dDOn80S') || !cookie.includes('HM4hUBT0dDOn80T')) {
    //     console.log('Get cookie failed ');
    //     return;
    // }

    // request an item detail page
    // console.log("=========== print cookie: ============")
    // console.log(cookie)
    // let postUrl = 'http://wenshu.court.gov.cn/website/parse/rest.q4w';
    // let config = {
    //     headers: {
    //         'Host': 'wenshu.court.gov.cn',
    //         'Accept': 'application/json, text/javascript, */*; q=0.01',
    //         'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
    //         'Content-Type': 'application/x-www-form-urlencoded',
    //         'Referer': 'http://wenshu.court.gov.cn/website/wenshu/181217BMTKHNT2W0/index.html',
    //         'Cookie': cookie
    //     },
    //     transformRequest: [function (data) {
    //             let retData = '';
    //             for (let param in data) {
    //                 retData += encodeURIComponent(param) + '=' + encodeURIComponent(data[param]) + '&';
    //             }
    //             return retData;
    //         }]
    // };
    // let detailBody = {
    //     'docId': '6dd3f5145ca9492198b06a7ce72fe74b',
    //     'ciphertext': cipherText(),
    //     '__RequestVerificationToken': random(24),
    //     'cfg': 'com.lawyee.judge.dc.parse.dto.SearchDataDsoDTO@docInfoSearch'
    // };
    // let response = await axios.default.post(postUrl, detailBody, config);
    // if (response.status === 200) {
    //     let text = DES3.decrypt(response.data.result, response.data.secretKey);
    //     console.log(text);
    // }
}
//# sourceMappingURL=ruishuCracker.js.map

// test code, run 'node service/ruishu/crack.js'
// get_cookies_async().then(console.log).catch(console.err);

function update_cookies() {
    
    get_cookies_async().then(function (result) {
        fs.writeFile('./cookies.txt', result, function(err) { });
        // console.log(result);
    }).catch(function (e) {
        fs.writeFile('./cookies.txt', 'fuck error', function(err) { });
    });
    return 0;
}

// update_cookies();


// function sleep(span) {
//     for(var start = new Date; new Date - start <= span;) {}
// }


// console.log("+++++++++++++++++"+cookies_wrapper());
