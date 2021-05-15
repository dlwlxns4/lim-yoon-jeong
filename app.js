// express 서버를 위한 모듈
const express = require('express');
const http = require('http');
const static = require('serve-static');
const path = require('path');

const bodyParser = require('body-parser');
const cookieParser = require('cookie-parser');
const expressSession = require('express-session');

const cors = require('cors');

const expressErroHandler = require('express-error-handler');

const config = require('./config/config');

//var database_loader = require('./database/database_loader');
const route_loader = require('./router/router_loader');

// 소켓 통신으로 받은 데이터를 블록체인에 저장하기 위한 모듈
const attendance = require('./router/attendance');

//===== Passport 사용 =====//
//var passport = require('passport');
//var flash = require('connect-flash');

// 서버 객체
const app = express(); 

// 뷰 관련 설정
app.set('views', __dirname + '/views');
app.set('view engine', 'ejs');

// port 번호 설정
app.set('port', process.env.PORT || config.server_port);

// get 방식
app.use('/public', static(path.join(__dirname, 'public')));

// post 방식
app.use(bodyParser.urlencoded({extended:false})); 
app.use(bodyParser.json()); 

// 세션 추가
app.use(cookieParser());
app.use(expressSession({
    secret:'my key',
    resave:true,
    saveUninitialized:true
}));

app.use(cors());

//===== Passport 초기화 및 로그인 세션유지 =====//
//app.use(passport.initialize());
//app.use(passport.session());
//app.use(flash());

const router = express.Router();
route_loader.init(app, router);

// passport 설정
//var configPassport = require('./config/configPassport');
//configPassport(app, passport);

// passport 관련 함수 라우팅
//var userPassport = require('./router/user');
//userPassport(app, passport);

// 등록된 라우터 패스가 없는 경우
const errorHandler = expressErroHandler({
    static: {
        '404': './public/404.html'
    }
});


app.use(expressErroHandler.httpError(404));
app.use(errorHandler);

const server = http.createServer(app).listen(app.get('port'), function() {    
    console.log('익스프레스로 웹 서버를 실행함 : ' + app.get('port'));
    
    //database_loader.init(app, config);
});

// socket 서버 실행
const socketio = require('socket.io')(server);
socketio.sockets.on('connection', (socket) => {
    socket.on('streaming', (data) => {
		console.log(data);
        attendance.send(data);
	});
});
console.log('소켓 서버 실행 완료.');