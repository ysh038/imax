# CGV 신규 시스템 API 관찰 기록

- 녹화 시각: 2026-08-20 16:47:01
- 수집 요청: 166건 / 고유 엔드포인트: 24개

자동 생성 문서입니다. `tools/record_api.py`를 다시 돌리면 갱신됩니다.

## 엔드포인트 목록

| 호출수 | 상태 | 엔드포인트 |
| ---: | --- | --- |
| 84 | 200 | `GET https://api.cgv.co.kr/com/bznsCom/screnMng/checkScrenUrlValid?coCd&expoChnlCd&pcUrl` |
| 18 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchMovScnInfo?coCd&rtctlScopCd&scnYmd&siteNo` |
| 5 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchGradByRpsntGrad?coCd` |
| 5 | 200 | `GET https://cgv.co.kr/api/v1/content/site/searchAllRegionAndSite?coCd&lntd&lttd` |
| 5 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchSiteScnscYmdListBySite?coCd&siteNo` |
| 4 | 200 | `GET https://api.cgv.co.kr/met/dsp/scrDsp/searchScrDspMainLogoCpot?coCd&ombScrenId` |
| 4 | 200 | `GET https://ad.cgv.co.kr/NetInsight/text/CGV/CGV_2025/PC@PC_AD` |
| 4 | 200 | `GET https://cgv.co.kr/?_rsc` |
| 4 | 204 | `POST https://cgv.co.kr/cdn-cgi/rum` |
| 3 | 200 | `GET https://cgv.co.kr/api/v1/activity/resv/actResv/searchHeaderActSiteList?bzplcTypCd&coCd` |
| 3 | 200 | `GET https://cgv.co.kr/api/v1/content/site/searchAllRegionAndSite?coCd` |
| 3 | 200 | `GET https://cgv.co.kr/api/v1/member/cust/info/searchMktRcvIagrYn` |
| 3 | 200 | `POST https://api.cgv.co.kr/com/bznsCom/mngrNtce/selectMngrNtceProcedure` |
| 3 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchRegnList?coCd&lntd&lttd` |
| 3 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchLastScnDay?coCd` |
| 2 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchOnlyCgvMovList?coCd` |
| 2 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchAtktTopPostrList?attrCd&coCd&div&movNm` |
| 2 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchSscnsCdList?coCd` |
| 2 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchSscnsSchdExistList?coCd&scnYmd&siteNo` |
| 2 | 200 | `GET https://cgv.co.kr/api/v1/booking/searchScnsMngList?coCd&siteNo` |
| 2 | 200 | `GET https://cgv.co.kr/api/v1/common/bznsCom/mov/searchRtktCntlYn?coCd&rtctlScopCd&scnSseq&scnYmd&scnsNo&siteNo` |
| 1 | 200 | `GET https://oidc.cgv.co.kr/cjone/getCjssoq?ssoCheck` |
| 1 | 0 | `GET https://nsso.cjone.com/findCookieRedirect.jsp?cjssoq&returnUrl` |
| 1 | 200 | `GET https://cdn.cgv.co.kr/cgvpomscontent/static/public/animations/mainTab/CGV_Micro_interactions_Motion_Tap_bar_Taga_x2.json` |

## 상세

### `GET https://api.cgv.co.kr/com/bznsCom/screnMng/checkScrenUrlValid?coCd&expoChnlCd&pcUrl`

- 실제 URL: `https://api.cgv.co.kr/com/bznsCom/screnMng/checkScrenUrlValid?coCd=A420&pcUrl=%2Fcnm%2FmovieBook&expoChnlCd=01`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook, https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "coCd": "A420",
    "pcUrlYn": "Y",
    "custLginYn": "N"
  }
}
```

### `GET https://cgv.co.kr/api/v1/booking/searchMovScnInfo?coCd&rtctlScopCd&scnYmd&siteNo`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchMovScnInfo?coCd=A420&siteNo=0013&scnYmd=20260820&rtctlScopCd=08`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{"statusCode":0,"statusMessage":"조회 되었습니다.","data":[{"coCd":"A420","siteNo":"0013","siteNm":"CGV 용산아이파크몰","scnsNo":"001","scnsNm":"1관 (Laser)","expoScnsNm":"1관 (Laser)","scnsEnm":"CINEMA 1","atktPsblQty":"8","scnYmd":"20260820","scnSseq":"4","prodNo":"20055710","expoProdNm":"오디세이(굿즈상영회)","engProdNm":"The Odyssey","prodNm":"오디세이(굿즈상영회)","movkndCd":"02","movkndDsplNm":"2D","movkndDsplEnm":"2D","cratgClsCd":"02","cratgClsNm":"15세이상관람가","salsTznCd":"26","salsTznNm":"일반","scnsrtTm":"1830","scnendTm":"2132","salEndTm":"1845","sascnsGradCd":"01","sortOseq":"5","sascnsGradNm":"일반","tcscnsGradCd":"01","tcscnsGradNm":"일반","stcnt":"204","cpSeatCnt":"204","frSeatCnt":"0","cntlYn":"N","crntrvDsplYn":"N","hotdlYn":"N","dblfrNo":null,"dblfrRpsntYn":null,"iceconYn":"N","arthsYn":"N","srlsYn":"N","childnMovYn":"N","movclsCd":"01","movclsNm":"영화","speclIndctTypCd":"01","movTirCd":"01","siteGradCd":"01","srvltKindCd":"01","slddKindCd":"01","sesnNo":null,"movNo":"30001323","movNm":"오디세이","movEnm":"The Odyssey","mvSeatCnt":"2","movfNo":"50002601","bzplcNo":"0013001","vatincYn":"Y","prdtypCd":"01","prddtlTypCd":"0101","prdcmpTypCd":"01","cxprdYn":"N","scnsGradCd":"0101","prcrulDivCd":"01","videoAddexpCd":"0038","videoAddexpCdNm":"기타","videoAddexpCont":"굿즈상영회","sbtdivCd":null,"sbtdivNm":null,"physcFnm":"30001323_185.jpg","physcFilePathnm":"030001/30001323/30001323_185.jpg","frtmpSeatCnt":"0","hotdlDtlNo":null,"rlMovStartTm":"1840","prmddNo":null,"prmddNm":null,"prodImg":null,"cndProdYn":null,"cndsaTypCd":null,"cndSalYnList":null},{"coCd":"A420","siteNo":"0013","siteNm":"CGV 용산아이파크몰","scnsNo":"001","scnsNm":"1관 (Laser)","expoScnsNm":"1관 (Laser)","scnsEnm":"CINEMA 1","atktPsblQty":"8","scnYmd":"20260820","scnSseq":"5","prodNo":"20054562","expoProdNm":"오디세이","engProdNm":"The Odyssey","prodNm":"오
... (총 30026자, 원문은 discovery/ 참고)
```

### `GET https://cgv.co.kr/api/v1/booking/searchGradByRpsntGrad?coCd`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchGradByRpsntGrad?coCd=A420`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "tcscnsList": [],
    "sascnsList": []
  }
}
```

### `GET https://cgv.co.kr/api/v1/content/site/searchAllRegionAndSite?coCd&lntd&lttd`

- 실제 URL: `https://cgv.co.kr/api/v1/content/site/searchAllRegionAndSite?coCd=A420&lttd=37.48708514214808&lntd=127.11893831194024`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "movInfo": null,
    "kndInfo": null,
    "regionInfo": [
      {
        "comCdval": "01",
        "comCdvalNm": "서울",
        "cnt": "37",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "02",
        "comCdvalNm": "경기",
        "cnt": "69",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "03",
        "comCdvalNm": "인천",
        "cnt": "16",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "04",
        "comCdvalNm": "강원",
        "cnt": "6",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "05",
        "comCdvalNm": "대전/충청",
        "cnt": "26",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "06",
        "comCdvalNm": "대구",
        "cnt": "11",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "07",
        "comCdvalNm": "부산/울산",
        "cnt": "19",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "08",
        "comCdvalNm": "경상",
        "cnt": "21",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "09",
        "comCdvalNm": "광주/전라/제주",
        "cnt": "28",
        "newOpenBzplcCnt": "N"
      }
    ],
    "siteInfo": [
      {
        "regnGrpCd": "01",
        "siteNo": "0056",
        "siteNm": "강남",
        "distance": "8.32701255750797391219366395085247707036E00"
      },
      {
        "regnGrpCd": "01",
        "siteNo": "0001",
        "siteNm": "강변",
        "distance": "5.74306880709973354917439290381265194221E00"
      },
      {
        "regnGrpCd": "01",
        "siteNo": "0229",
        "siteNm": "건대입구",
        "distance": "7.47141045018048951127903928531044686696E00"
      },
      {
        "regnGrpCd": "01",
        "siteN
... (총 30049자, 원문은 discovery/ 참고)
```

### `GET https://cgv.co.kr/api/v1/booking/searchSiteScnscYmdListBySite?coCd&siteNo`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchSiteScnscYmdListBySite?coCd=A420&siteNo=0013`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": [
    {
      "scnYmd": "20260820",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260821",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260822",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260823",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260824",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260825",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260826",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260827",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260828",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260829",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260830",
      "hldyYn": "N"
    },
    {
      "scnYmd": "20260902",
      "hldyYn": "N"
    }
  ]
}
```

### `GET https://api.cgv.co.kr/met/dsp/scrDsp/searchScrDspMainLogoCpot?coCd&ombScrenId`

- 실제 URL: `https://api.cgv.co.kr/met/dsp/scrDsp/searchScrDspMainLogoCpot?coCd=A420&ombScrenId=MMN-S00007`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook, https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "coCd": "A420",
    "unitCpotRelNo": 369,
    "banrSeq": "2",
    "banrTitl": "기본 이미지",
    "imageHtmlDivCd": "1",
    "fixYn": "N",
    "wghtUseYn": "N",
    "expoWghtVal": 0,
    "flashMtnTypCd": "9",
    "lnkUseYn": "N",
    "prty": 1,
    "title": null,
    "subTitle": null,
    "butnNm": null,
    "cntsDtlCont": null,
    "bkgrColorStartVal": "FDF200",
    "bkgrColorTendVal": "BEF34C",
    "htmlTypCd": "1",
    "banrLnkTypCd": null,
    "evntNo": null,
    "movNo": null,
    "prodNo": null,
    "basLnkUrl": null,
    "basLnkInrMvYn": "N",
    "pcLnkIntlckYn": "N",
    "pcUrl": null,
    "pcInrMvYn": "N",
    "ntivAppIntlckYn": "N",
    "andrdUrl": null,
    "iphonUrl": null,
    "mediaDivCd": "01",
    "accbWordCont": "CGV 로고 이미지",
    "physcFnm": "4c8da3708290405bb6400a6a553cade2.svg",
    "physcFilePathnm": "cgvpomscontent/ips/unitCnts/2025/1114"
  }
}
```

### `GET https://ad.cgv.co.kr/NetInsight/text/CGV/CGV_2025/PC@PC_AD`

- 실제 URL: `https://ad.cgv.co.kr/NetInsight/text/CGV/CGV_2025/PC@PC_AD`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook, https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
<?xml version='1.0' encoding='UTF-8' ?>
<MOVIE_AD>
	<CREATIVE_ID><![CDATA[]]></CREATIVE_ID>
	<AD_Type><![CDATA[2]]></AD_Type>
	<AD_MOVIEIDX><![CDATA[30001326]]></AD_MOVIEIDX>
	<AD_MOVIE_NM><![CDATA[명탐정 코난:하이웨이의 타천사]]></AD_MOVIE_NM>
	<AD_DESCRIPTION_NM_1><![CDATA[모두를 지키기 위한]]></AD_DESCRIPTION_NM_1>
	<AD_DESCRIPTION_NM_2><![CDATA[리밋 브레이크 액션]]></AD_DESCRIPTION_NM_2>
	<AD_CLIP_URL><![CDATA[https://adimg.cgv.co.kr/prod/creative/20260730/Conan/image/250x310.jpg]]></AD_CLIP_URL>
	<AD_CLIP_DETAIL_URL><![CDATA[https://ad.cgv.co.kr/click/CGV/CGV_2025/PC@PC_AD?ads_id%3d54759%26creative_id%3d84831%26click_id%3d105722%26content_series%3d%26event%3d]]></AD_CLIP_DETAIL_URL>
	<ad_btn_type><![CDATA[자세히보기]]></ad_btn_type>
	<AD_CNT_URL><![CDATA[http://ad.cgv.co.kr/NetInsight/imp/CGV/CGV_2025/PC@PC_AD?ads_id%3d54759%26creative_id%3d84831]]></AD_CNT_URL>
</MOVIE_AD>
```

### `GET https://cgv.co.kr/?_rsc`

- 실제 URL: `https://cgv.co.kr/?_rsc=sxztl`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook, https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
0:["cnO_PWx_zONAb9OjCVtx8",[["children","(home)","children","__PAGE__",["__PAGE__",{}],null,null]]]

```

### `POST https://cgv.co.kr/cdn-cgi/rum`

- 실제 URL: `https://cgv.co.kr/cdn-cgi/rum?`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook, https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
{
  "memory": {
    "totalJSHeapSize": 34936395,
    "usedJSHeapSize": 25810323,
    "jsHeapSizeLimit": 4395630592
  },
  "resources": [],
  "referrer": "",
  "eventType": 1,
  "firstPaint": 2380,
  "firstContentfulPaint": 2380,
  "startTime": 1787210562964,
  "versions": {
    "fl": "2024.11.0",
    "js": "2026.6.0",
    "timings": 2
  },
  "pageloadId": "8f77ad79-ab8d-42b2-87ed-42694aa7c44c",
  "location": "https://cgv.co.kr/cnm/movieBook",
  "nt": "navigate",
  "timingsV2": {
    "nextHopProtocol": "h2",
    "domainLookupStart": 1073.6000003814697,
    "domainLookupEnd": 1073.6000003814697,
    "connectStart": 1073.6000003814697,
    "connectEnd": 1112.8000001907349,
    "requestStart": 1113,
    "responseStart": 1384.1000003814697,
    "responseEnd": 1420.3000001907349,
    "domInteractive": 1474.7000002861023,
    "domComplete": 3441.5,
    "loadEventStart": 3441.5,
    "loadEventEnd": 3441.5,
    "finalResponseHeadersStart": 1384.1000003814697,
    "firstInterimResponseStart": 0,
    "transferSize": 9939,
    "decodedBodySize": 66847
  },
  "dt": "",
  "siteToken": "f0acf9af56d54875af96eda29f2a92c9",
  "st": 2
}
```

응답 본문:

```json
(없음)
```

### `GET https://cgv.co.kr/api/v1/activity/resv/actResv/searchHeaderActSiteList?bzplcTypCd&coCd`

- 실제 URL: `https://cgv.co.kr/api/v1/activity/resv/actResv/searchHeaderActSiteList?coCd=A420&bzplcTypCd=11`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "bzplcTypCd": "11",
    "bzplcTypNm": "미션브레이크",
    "actSiteList": [
      {
        "coCd": "A420",
        "siteNo": "0013",
        "siteNm": "용산아이파크몰",
        "bzplcNo": "0013011",
        "bzplcGuidDsc": "<p>영화관 X 방탈출 테마체험 공간</p>",
        "bzplcPrkgGuidDsc": "<p>- 아이파크몰 주차장 이용<br>- 미션브레이크 이용 고객 3시간 무료<br>&nbsp; &nbsp;(영화 관람과 합산 불가)<br>&nbsp;</p>",
        "imageUrl": "cgvpsms/prdinfo/SOM/2025/0714/fBCRNWLlweMtzpPUm55A.png",
        "telNo": "0220122971",
        "oftenRnum": "6"
      }
    ]
  }
}
```

### `GET https://cgv.co.kr/api/v1/content/site/searchAllRegionAndSite?coCd`

- 실제 URL: `https://cgv.co.kr/api/v1/content/site/searchAllRegionAndSite?coCd=A420`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "movInfo": null,
    "kndInfo": null,
    "regionInfo": [
      {
        "comCdval": "01",
        "comCdvalNm": "서울",
        "cnt": "37",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "02",
        "comCdvalNm": "경기",
        "cnt": "69",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "03",
        "comCdvalNm": "인천",
        "cnt": "16",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "04",
        "comCdvalNm": "강원",
        "cnt": "6",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "05",
        "comCdvalNm": "대전/충청",
        "cnt": "26",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "06",
        "comCdvalNm": "대구",
        "cnt": "11",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "07",
        "comCdvalNm": "부산/울산",
        "cnt": "19",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "08",
        "comCdvalNm": "경상",
        "cnt": "21",
        "newOpenBzplcCnt": "N"
      },
      {
        "comCdval": "09",
        "comCdvalNm": "광주/전라/제주",
        "cnt": "28",
        "newOpenBzplcCnt": "N"
      }
    ],
    "siteInfo": [
      {
        "regnGrpCd": "01",
        "siteNo": "0056",
        "siteNm": "강남",
        "distance": null
      },
      {
        "regnGrpCd": "01",
        "siteNo": "0001",
        "siteNm": "강변",
        "distance": null
      },
      {
        "regnGrpCd": "01",
        "siteNo": "0229",
        "siteNm": "건대입구",
        "distance": null
      },
      {
        "regnGrpCd": "01",
        "siteNo": "0366",
        "siteNm": "고덕강일",
        "distance": null
      },
      {
        "regnGrpCd": "01",
        "siteNo"
... (총 22776자, 원문은 discovery/ 참고)
```

### `GET https://cgv.co.kr/api/v1/member/cust/info/searchMktRcvIagrYn`

- 실제 URL: `https://cgv.co.kr/api/v1/member/cust/info/searchMktRcvIagrYn`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": null
}
```

### `POST https://api.cgv.co.kr/com/bznsCom/mngrNtce/selectMngrNtceProcedure`

- 실제 URL: `https://api.cgv.co.kr/com/bznsCom/mngrNtce/selectMngrNtceProcedure`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
{
  "coCd": "A420",
  "custNo": "",
  "ntceExpoClsCd": "02",
  "ntceExpoDtlClsCd": "04",
  "prodNo": "",
  "siteNo": "",
  "bzplcNo": "",
  "expoChnlCd": "01"
}
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "errCd": null,
    "errMsg": null,
    "existYn": "N",
    "list": null
  }
}
```

### `GET https://cgv.co.kr/api/v1/booking/searchRegnList?coCd&lntd&lttd`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchRegnList?coCd=A420&lntd=127.11893831194024&lttd=37.48708514214808`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": [
    {
      "coCd": "A420",
      "regnGrpCd": "01",
      "regnGrpNm": "서울",
      "schdCnt": "823",
      "newOpenBzplcYn": "N",
      "siteList": [
        {
          "coCd": "A420",
          "siteNo": "0056",
          "siteNm": "강남",
          "bzplcOperStusNm": "운영중",
          "distance": null,
          "movkndCd": null
        },
        {
          "coCd": "A420",
          "siteNo": "0001",
          "siteNm": "강변",
          "bzplcOperStusNm": "운영중",
          "distance": null,
          "movkndCd": null
        },
        {
          "coCd": "A420",
          "siteNo": "0229",
          "siteNm": "건대입구",
          "bzplcOperStusNm": "운영중",
          "distance": null,
          "movkndCd": null
        },
        {
          "coCd": "A420",
          "siteNo": "0366",
          "siteNm": "고덕강일",
          "bzplcOperStusNm": "운영중",
          "distance": null,
          "movkndCd": null
        },
        {
          "coCd": "A420",
          "siteNo": "0010",
          "siteNm": "구로",
          "bzplcOperStusNm": "운영중",
          "distance": null,
          "movkndCd": null
        },
        {
          "coCd": "A420",
          "siteNo": "0063",
          "siteNm": "대학로",
          "bzplcOperStusNm": "운영중",
          "distance": null,
          "movkndCd": null
        },
        {
          "coCd": "A420",
          "siteNo": "0252",
          "siteNm": "동대문",
          "bzplcOperStusNm": "운영중",
          "distance": null,
          "movkndCd": null
        },
        {
          "coCd": "A420",
          "siteNo": "0230",
          "siteNm": "등촌",
          "bzplcOperStusNm": "운영중",
          "distance": null,
          "movkndCd": null
        },
        {
          "coCd": "A420",
      
... (총 35862자, 원문은 discovery/ 참고)
```

### `GET https://cgv.co.kr/api/v1/booking/searchLastScnDay?coCd`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchLastScnDay?coCd=A420`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": [
    {
      "scnYmd": "20260920",
      "hldyYn": null
    }
  ]
}
```

### `GET https://cgv.co.kr/api/v1/booking/searchOnlyCgvMovList?coCd`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchOnlyCgvMovList?coCd=A420`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": [
    {
      "coCd": "A420",
      "movNo": "30001382",
      "movNm": "터치드 콘서트 [하이라이트 포] - 더 무비",
      "i320Fnm": "30001382_320.jpg",
      "scnBssTm": null,
      "cratgClsCd": null,
      "atktRate": null,
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001348",
      "movNm": "에이티즈 - 라이트 더 웨이 인 시네마",
      "i320Fnm": "30001348_320.jpg",
      "scnBssTm": null,
      "cratgClsCd": null,
      "atktRate": null,
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001394",
      "movNm": "BOYNEXTDOOR TOUR 'KNOCK ON Vol.2' IN JAPAN",
      "i320Fnm": "30001394_320.jpg",
      "scnBssTm": null,
      "cratgClsCd": null,
      "atktRate": null,
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001373",
      "movNm": "(라이브뷰잉)IDOLiSH7 VISIBLIVE TOUR '4WARD JOURNEY' Live Viewing",
      "i320Fnm": "30001373_320.jpg",
      "scnBssTm": null,
      "cratgClsCd": null,
      "atktRate": null,
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001302",
      "movNm": "파뿌리 24- 좀비 아일랜드",
      "i320Fnm": "30001302_320.png",
      "scnBssTm": null,
      "cratgClsCd": null,
      "atktRate": null,
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001401",
      "movNm": "산산조각",
      "i320Fnm": "30001401_320.jpg",
      "scnBssTm": null,
      "cratgClsCd": null,
      "atktRate": null,
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001445",
      "movNm": "2026 KBO x CGV 야구의 날 뷰잉파티",
      "i320Fnm": "30001445_320.jpg",
      "scnBssTm": null,
      "cratgClsCd": null,
      "atktRate": null,
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001407",
... (총 2473자, 원문은 discovery/ 참고)
```

### `GET https://cgv.co.kr/api/v1/booking/searchAtktTopPostrList?attrCd&coCd&div&movNm`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchAtktTopPostrList?coCd=A420&movNm=&div=&attrCd=`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": [
    {
      "coCd": "A420",
      "movNo": "30001323",
      "movNm": "오디세이",
      "i320Fnm": "30001323_320.jpg",
      "scnBssTm": "172",
      "cratgClsCd": "02",
      "atktRate": "75.26",
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001192",
      "movNm": "스파이더맨-브랜드 뉴 데이",
      "i320Fnm": "30001192_320.jpg",
      "scnBssTm": "145",
      "cratgClsCd": "03",
      "atktRate": "11.76",
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001222",
      "movNm": "인시디어스-그들이 넘어왔다",
      "i320Fnm": "30001222_320.jpg",
      "scnBssTm": "106",
      "cratgClsCd": "02",
      "atktRate": "2.24",
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001326",
      "movNm": "명탐정 코난-하이웨이의 타천사",
      "i320Fnm": "30001326_320.jpg",
      "scnBssTm": "109",
      "cratgClsCd": "03",
      "atktRate": "1.56",
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001350",
      "movNm": "경주기행",
      "i320Fnm": "30001350_320.jpg",
      "scnBssTm": "111",
      "cratgClsCd": "02",
      "atktRate": "1.34",
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001359",
      "movNm": "마루 밑 아리에티",
      "i320Fnm": "30001359_320.jpg",
      "scnBssTm": "94",
      "cratgClsCd": "04",
      "atktRate": "1.08",
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001045",
      "movNm": "사랑의 하츄핑-고래보석의 전설",
      "i320Fnm": "30001045_320.jpg",
      "scnBssTm": "105",
      "cratgClsCd": "04",
      "atktRate": "1.06",
      "mblUrl": null
    },
    {
      "coCd": "A420",
      "movNo": "30001325",
      "movNm": "오케이 마담2",
      "i320Fnm": "30001325_320.jpg",
      "scnBssTm": "108",
  
... (총 14514자, 원문은 discovery/ 참고)
```

### `GET https://cgv.co.kr/api/v1/booking/searchSscnsCdList?coCd`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchSscnsCdList?coCd=A420`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "tcscnsCdList": [
      {
        "coCd": "A420",
        "sscnsNo": "8",
        "sscnsNm": "DOLBY ATMOS",
        "sscnsClsCd": "01",
        "movkndCd": "06",
        "movkndNm": "4DX 3D",
        "tcscnsGradCd": "02",
        "imageUrl": "cgvpomscontent/ips/sscns/2025/0716eddc934d3726415691ef9fe503b73505.jpg"
      },
      {
        "coCd": "A420",
        "sscnsNo": "4",
        "sscnsNm": "SCREENX",
        "sscnsClsCd": "01",
        "movkndCd": "08",
        "movkndNm": "4DX 2D",
        "tcscnsGradCd": "02",
        "imageUrl": "cgvpomscontent/ips/sscns/2026/0519a662ae61a06746b89e0813c63eea387e.png"
      },
      {
        "coCd": "A420",
        "sscnsNo": "3",
        "sscnsNm": "ULTRA 4DX",
        "sscnsClsCd": "01",
        "movkndCd": "09",
        "movkndNm": "4DX 2D(4K)",
        "tcscnsGradCd": "02",
        "imageUrl": "cgvpomscontent/ips/sscns/2025/0716819c5ad6c56d427ab2bf8a2802e3130b.jpg"
      },
      {
        "coCd": "A420",
        "sscnsNo": "2",
        "sscnsNm": "4DX",
        "sscnsClsCd": "01",
        "movkndCd": "03",
        "movkndNm": "2D(4K)",
        "tcscnsGradCd": "01",
        "imageUrl": "cgvpomscontent/ips/sscns/2025/0714d71cc447fe4047c4b1f73fadb8580cf6.jpg"
      },
      {
        "coCd": "A420",
        "sscnsNo": "1",
        "sscnsNm": "IMAX",
        "sscnsClsCd": "01",
        "movkndCd": "04",
        "movkndNm": "3D",
        "tcscnsGradCd": "01",
        "imageUrl": "cgvpomscontent/vps/sscns/2025/0714c2026b4931014440a2bf924941c957a3.mp4"
      }
    ],
    "prestigeList": [
      {
        "coCd": "A420",
        "sscnsNo": "16",
        "sscnsNm": "PREMIUM",
        "sscnsClsCd": "02",
        "movkndCd": "01",
        "movkndNm": "필름",
        "
... (총 3485자, 원문은 discovery/ 참고)
```

### `GET https://cgv.co.kr/api/v1/booking/searchSscnsSchdExistList?coCd&scnYmd&siteNo`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchSscnsSchdExistList?coCd=A420&siteNo=0013&scnYmd=20260820`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": [
    {
      "coCd": "A420",
      "comCd": "TCSCNS_GRAD_CD",
      "comCdval": "04",
      "comCdvalNm": "SCREENX",
      "schdCnt": "3",
      "newOpenBzplcYn": "N",
      "sscnsRcmSiteList": null,
      "sscnsSiteList": null
    },
    {
      "coCd": "A420",
      "comCd": "TCSCNS_GRAD_CD",
      "comCdval": "02",
      "comCdvalNm": "4DX",
      "schdCnt": "2",
      "newOpenBzplcYn": "N",
      "sscnsRcmSiteList": null,
      "sscnsSiteList": null
    },
    {
      "coCd": "A420",
      "comCd": "TCSCNS_GRAD_CD",
      "comCdval": "03",
      "comCdvalNm": "아이맥스",
      "schdCnt": "1",
      "newOpenBzplcYn": "N",
      "sscnsRcmSiteList": null,
      "sscnsSiteList": null
    },
    {
      "coCd": "A420",
      "comCd": "SASCNS_GRAD_CD",
      "comCdval": "08",
      "comCdvalNm": "프리미엄관",
      "schdCnt": "6",
      "newOpenBzplcYn": "N",
      "sscnsRcmSiteList": null,
      "sscnsSiteList": null
    },
    {
      "coCd": "A420",
      "comCd": "SASCNS_GRAD_CD",
      "comCdval": "12",
      "comCdvalNm": "아트하우스",
      "schdCnt": "13",
      "newOpenBzplcYn": "N",
      "sscnsRcmSiteList": null,
      "sscnsSiteList": null
    }
  ]
}
```

### `GET https://cgv.co.kr/api/v1/booking/searchScnsMngList?coCd&siteNo`

- 실제 URL: `https://cgv.co.kr/api/v1/booking/searchScnsMngList?coCd=A420&siteNo=0013`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "specialScreenYn": "Y"
  }
}
```

### `GET https://cgv.co.kr/api/v1/common/bznsCom/mov/searchRtktCntlYn?coCd&rtctlScopCd&scnSseq&scnYmd&scnsNo&siteNo`

- 실제 URL: `https://cgv.co.kr/api/v1/common/bznsCom/mov/searchRtktCntlYn?coCd=A420&siteNo=0013&scnYmd=20260820&scnsNo=006&scnSseq=4&rtctlScopCd=08`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook/cinema

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "rtktCntlYn": "N"
  }
}
```

### `GET https://oidc.cgv.co.kr/cjone/getCjssoq?ssoCheck`

- 실제 URL: `https://oidc.cgv.co.kr/cjone/getCjssoq?ssoCheck=N`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook

요청 본문:

```json
(없음)
```

응답 본문:

```json
{
  "statusCode": 0,
  "statusMessage": "조회 되었습니다.",
  "data": {
    "cjssoq": "ohuZ30u52a+NnyIvuOon8Vc4WAD2fFZ2nqTCsfBMzw7QdNR9uEVZn7tWnm+/+pPtmmHgg06GDBekBvZ5iOTFzkFENlhwOWVMNFFMcThQUGhQaU9yYUJsRXd4TVkyQW5rUXRiZW5saHo2Rk1vMjI1cFhOQmYzMUhTZnlnUmxjZzY=",
    "ssoHealth": null,
    "ssoMbrNo": null,
    "chkAuth": null
  }
}
```

### `GET https://nsso.cjone.com/findCookieRedirect.jsp?cjssoq&returnUrl`

- 실제 URL: `https://nsso.cjone.com/findCookieRedirect.jsp?cjssoq=&returnUrl=https%3A%2F%2Fcgv.co.kr%2Fcnm%2FmovieBook`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook

요청 본문:

```json
(없음)
```

응답 본문:

```json
(없음)
```

### `GET https://cdn.cgv.co.kr/cgvpomscontent/static/public/animations/mainTab/CGV_Micro_interactions_Motion_Tap_bar_Taga_x2.json`

- 실제 URL: `https://cdn.cgv.co.kr/cgvpomscontent/static/public/animations/mainTab/CGV_Micro_interactions_Motion_Tap_bar_Taga_x2.json`
- 호출 페이지: https://cgv.co.kr/cnm/movieBook

요청 본문:

```json
(없음)
```

응답 본문:

```json
{"v":"4.8.0","meta":{"g":"LottieFiles AE 3.5.9","a":"","k":"","d":"","tc":""},"fr":30,"ip":0,"op":70,"w":700,"h":700,"nm":"CGV_Micro interactions_Motion_Tap bar_Taga_8","ddd":0,"assets":[{"id":"imgSeq_0","w":700,"h":700,"t":"seq","u":"","p":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAArwAAAK8CAYAAAANumxDAAAACXBIWXMAAAABAAAAAQBPJcTWAAAAJHpUWHRDcmVhdG9yAAAImXNMyU9KVXBMK0ktUnBNS0tNLikGAEF6Bs5qehXFAAAgAElEQVR4nOzdeZAs61nf+ed5M6uqu0/3OX22ux4twQS6ArFY3AlkEwHMmAB7DAZMxLUxFjYwDDGDGAzDOiZgJBgW2ZoZMLJkNAiBbA8ylzEIjACzemyDxCBGCHQttF3de8/dztZ9Tm+1ZL7P/JGV1VlZmVVZVVnV2/cTkXH61OnuW9lSdf7qyed9XhEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACgOj3qJwAAp4Et6Pepitgivi8AnCUEXgAosagQuyiEYwAodqJ+mQNA3U5aqJ0VYRjAWXYmftEDwFkJttMg
... (총 30028자, 원문은 discovery/ 참고)
```
