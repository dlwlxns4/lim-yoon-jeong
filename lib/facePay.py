import face_recognition
import pickle
import dlib
import numpy as np
import cv2
import socketio
import sys
from PyQt5.QtWidgets import *
from threading import Thread
import time
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import hashlib

sio = socketio.Client()
sio.connect('http://127.0.0.1:3300')

encoding_file = './encodings.pickle'
unknown_name = 'Unknown'
# Either cnn  or hog. The CNN method is more accurate but slower. HOG is faster but less accurate.
model_method = 'cnn'

RIGHT_EYE = list(range(36, 42))
LEFT_EYE = list(range(42, 48))
EYES = list(range(36, 48))

predictor_file = './model/shape_predictor_68_face_landmarks.dat'
MARGIN_RATIO = 1.5
OUTPUT_SIZE = (300, 300)

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor(predictor_file)

name = ''
pre_name = ''

# load the known faces and embeddings
data = pickle.loads(open(encoding_file, "rb").read())


class MyApp(QWidget):

    def __init__(self):
        super().__init__()
        self.initUI()

        # 막 해보는중.
        self.video = video(self, QSize(self.frame.width(), self.frame.height()))

    def initUI(self):
        self.setWindowTitle('얼굴 인식 기반 간편결제 시스템')
        self.move(100, 100)
        self.resize(1200, 800)

        hbox = QHBoxLayout()
        vbox = QVBoxLayout()

        vbox.addStretch(1)
        self.btnBreakfast = QPushButton('조식 \n3500', self)
        self.btnBreakfast.clicked.connect(self.decisionBreakFast)
        vbox.addWidget(self.btnBreakfast)

        self.btnLunch = QPushButton('중식 \n4000', self)
        self.btnLunch.clicked.connect(self.decisionLunch)
        vbox.addWidget(self.btnLunch)

        self.btnDinner = QPushButton('석식 \n5000', self)
        self.btnDinner.clicked.connect(self.decisionDinner)
        vbox.addWidget(self.btnDinner)

        vbox.addStretch(1)

        self.labelCode = QLabel('식별 코드 : ', self)
        font = self.labelCode.font()
        font.setPointSize(20)
        vbox.addWidget(self.labelCode)

        self.labelTotalrice = QLabel('총 금액 : ', self)
        font = self.labelTotalrice.font()
        font.setPointSize(20)
        vbox.addWidget(self.labelTotalrice)

        self.btnPay = QPushButton('결제하기', self)
        self.btnPay.setCheckable(True)
        self.btnPay.clicked.connect(self.pay)
        hbox.addWidget(self.btnPay)

        self.btnReset = QPushButton('초기화', self)
        self.btnReset.clicked.connect(self.init)
        hbox.addWidget(self.btnReset)

        vbox.addLayout(hbox)

        self.btnStart = QPushButton('시작하기', self)
        self.btnStart.clicked.connect(self.start)
        hbox.addWidget(self.btnStart)
        vbox.addStretch(1)

        self.frame = QLabel(self)
        self.frame.setFrameShape(QFrame.Panel)

        wholeHbox = QHBoxLayout()
        wholeHbox.addLayout(vbox)
        wholeHbox.addWidget(self.frame, 1)
        self.setLayout(wholeHbox)

        self.isNeedDetection = True
        self.show()

    def decisionBreakFast(self, e):
        self.labelTotalrice.setText('총 금액 : 3500')
        self.labelTotalrice.repaint()

    def decisionLunch(self, e):
        self.labelTotalrice.setText('총 금액 : 4000')
        self.labelTotalrice.repaint()

    def decisionDinner(self, e):
        self.labelTotalrice.setText('총 금액 : 5000')
        self.labelTotalrice.repaint()

    def pay(self, e):
        if self.btnPay.isChecked():
            self.btnPay.setText('결제종료')
            codeTag = self.labelCode.text().split()
            priceTag = self.labelTotalrice.text().split()

            if len(codeTag) == 4:
                code = codeTag[3]
            else:
                reply = QMessageBox.question(self, 'Message', '얼굴을 인식해 주십시오.',
                                             QMessageBox.Yes)

                if reply == QMessageBox.Yes:
                    self.btnPay.click()
                    return

            if len(priceTag) == 4:
                # self.btnPay.setEnabled(False)
                price = priceTag[3]
            else:
                reply = QMessageBox.question(self, 'Message', '메뉴를 선택해 주십시오.',
                                             QMessageBox.Yes)

                if reply == QMessageBox.Yes:
                    self.btnPay.click()
                    return

            # 소켓 서버에 인증 결과 전송
            payInfo = {'code': code, 'price': price}
            self.isProcessingPay = True
            sio.emit('pay', payInfo)

            while self.isProcessingPay:
                sio.on('pay', self.finish)
                
        else:
            self.btnPay.setText('결제하기')
            self.initTotalPrice()
            self.initCode()
            self.isNeedDetection = True

    def finish(self, result):
        print(result)
        # self.btnPay.setEnabled(True)
        self.isProcessingPay = False
        if result == 'completed':
            self.labelCode.setText('결제완료')
            self.labelCode.repaint()
        else:
            self.labelCode.setText('잔액부족')
            self.labelCode.repaint()

    def start(self, e):
        self.btnStart.setEnabled(False)
        self.video.startCam()

    def init(self, e):
        self.initCode()
        self.initTotalPrice()
        self.isNeedDetection = True

    def initTotalPrice(self):
        self.labelTotalrice.setText('총 금액 : ')
        self.labelTotalrice.repaint()

    def initCode(self):
        self.labelCode.setText('식별 코드 : ')
        self.labelCode.repaint()

    def recvImage(self, img):
        self.frame.setPixmap(QPixmap.fromImage(img))


class video(QObject):
    sendImage = pyqtSignal(QImage)

    def __init__(self, widget, size):
        super().__init__()
        self.widget = widget
        self.size = size
        self.sendImage.connect(self.widget.recvImage)

    def setOption(self, option):
        self.option = option

    def startCam(self):
        try:
            self.cap = cv2.VideoCapture(0)
        except Exception as e:
            print('Cam Error : ', e)
        else:
            self.bThread = True
            self.thread = Thread(target=self.threadFunc)
            self.thread.start()

    def stopCam(self):
        self.bThread = False
        bopen = False
        try:
            bopen = self.cap.isOpened()
            # sio.disconnect()
        except Exception as e:
            print('Error cam not opened')
        else:
            self.cap.release()

    def threadFunc(self):
        while self.bThread:
            success, image = self.cap.read()
            if success:
                # image_origin = image.copy()
                try:
                    image_origin = image[100:401, 170:451].copy()
                except Exception as e:
                    print(str(e))

                cv2.rectangle(image, (170, 100), (450, 400), (0, 255, 255), 1)
                (image_height, image_width) = image_origin.shape[:2]
                # detect image
                gray = cv2.cvtColor(image_origin, cv2.COLOR_BGR2GRAY)

                rects = detector(gray, 1)  # gray에 있는 얼굴들 get_frontal_face_detector을 통하여 전면 얼굴 검출하기

                if image is None:
                    print('--(!) No captured image -- Break!')
                    # close the video file pointers

                    self.cap.release()
                    # close the writer point
                    break

                # create image
                rgbData = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                h, w, ch = rgbData.shape
                bytesPerLine = ch * w
                img = QImage(rgbData.data, w, h, bytesPerLine, QImage.Format_RGB888)
                resizedImg = img.scaled(self.size.width(), self.size.height(), Qt.KeepAspectRatio)
                self.sendImage.emit(resizedImg)

                # cv2.imshow("", image)

                # Hit 'q' on the keyboard to quit!
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                global pre_name
                if str(rects) == "rectangles[]":
                    pre_name = ''

                # Input Data 전처리
                for (i, rect) in enumerate(rects):
                    (x, y, w, h) = self.getFaceDimension(rect)

                    # print(x,y,w,h)
                    if w > 120 and h > 120:
                        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

                        points = np.matrix([[p.x, p.y] for p in predictor(gray, rect).parts()])
                        show_parts = points[EYES]

                        right_eye_center = np.mean(points[RIGHT_EYE], axis=0).astype("int")
                        left_eye_center = np.mean(points[LEFT_EYE], axis=0).astype("int")

                        eye_delta_x = right_eye_center[0, 0] - left_eye_center[0, 0]
                        eye_delta_y = right_eye_center[0, 1] - left_eye_center[0, 1]
                        degree = np.degrees(np.arctan2(eye_delta_y, eye_delta_x)) - 180

                        eye_distance = np.sqrt((eye_delta_x ** 2) + (eye_delta_y ** 2))
                        aligned_eye_distance = left_eye_center[0, 0] - right_eye_center[0, 0]
                        scale = aligned_eye_distance / eye_distance

                        eyes_center = ((left_eye_center[0, 0] + right_eye_center[0, 0]) // 2,
                                       (left_eye_center[0, 1] + right_eye_center[0, 1]) // 2)

                        metrix = cv2.getRotationMatrix2D(eyes_center, degree, scale)
                        cv2.putText(image, "{:.5f}".format(degree),
                                    (right_eye_center[0, 0], right_eye_center[0, 1] + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                        warped = cv2.warpAffine(image_origin, metrix, (image_width, image_height),
                                                flags=cv2.INTER_CUBIC)

                        (startX, endX, startY, endY) = self.getCropDimension(rect, eyes_center)
                        croped = warped[startY:endY, startX:endX]

                        try:
                            output = cv2.resize(croped, OUTPUT_SIZE, cv2.INTER_AREA)
                        except Exception as e:
                            print(str(e))

                        # 전처리한 Input Data 얼굴인식
                        try:
                            if self.widget.isNeedDetection:
                                self.detectAndDisplay(output)
                        except Exception as e:
                            print(str(e))

                        for (i, point) in enumerate(show_parts):
                            x = point[0, 0]
                            y = point[0, 1]
                            cv2.circle(image, (x, y), 1, (0, 255, 255), -1)
            else:
                print('cam read errror')

            time.sleep(0.01)
            # time.sleep(0.3)

        print('thread finished')
        cv2.destroyAllWindows()

    # 사진 짜르기 메소드
    def getFaceDimension(self, rect):
        return (rect.left(), rect.top(), rect.right() - rect.left(), rect.bottom() - rect.top())

    def getCropDimension(self, rect, center):
        width = (rect.right() - rect.left())
        half_width = width // 2
        (centerX, centerY) = center
        startX = centerX - half_width
        endX = centerX + half_width
        startY = rect.top()
        endY = rect.bottom()
        return (startX, endX, startY, endY)

    # 얼굴인식후 표시 메소드
    def detectAndDisplay(self, image):
        global name, pre_name
        unknown_check = False

        start_time = time.time()
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        boxes = face_recognition.face_locations(rgb,
                                                model=model_method)
        encodings = face_recognition.face_encodings(rgb, boxes)
        names = []

        # loop over the facial embeddings
        for encoding in encodings:

            distance = face_recognition.face_distance(data["encodings"], encoding)

            distance_bool = []

            for i in distance:
                if i < 0.39:
                    distance_bool.append(True)
                else:
                    distance_bool.append(False)

            # check to see if we have found a match
            if True in distance_bool:
                matchedIdxs = [i for (i, b) in enumerate(distance_bool) if b]
                counts = {}

                for i in matchedIdxs:
                    name = data["names"][i]
                    counts[name] = counts.get(name, 0) + 1

                unknown_check = True

                name = max(counts, key=counts.get)

            if unknown_check == False:
                names.append("unknown_name")
                print("ch-unknown")
            else:
                names.append(name)
                print("no-unknwon")
            # print(names)

        # loop over the recognized faces
        for ((top, right, bottom, left), name) in zip(boxes, names):
            y = top - 15 if top - 15 > 15 else top + 15
            color = (0, 255, 0)
            line = 2
            if (name == "unknown_name"):
                color = (0, 0, 255)
                line = 1
                name = ''

            cv2.rectangle(image, (left, top), (right, bottom), color, line)
            y = top - 15 if top - 15 > 15 else top + 15
            cv2.putText(image, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX,
                        0.75, color, line)
        end_time = time.time()
        process_time = end_time - start_time
        print("=== A frame took {:.3f} seconds".format(process_time))
        # show the output image

        # cv2.imshow("Recognition", image)

        Date = str(time.localtime().tm_year) + "-" + str(time.localtime().tm_mon) + "-" + str(
            time.localtime().tm_mday) + "-" + str(time.localtime().tm_hour) + ":" + str(time.localtime().tm_min)
        print(name, Date)

        if pre_name == name:
            return

        if name != '':
            print('얼굴 인식됨.')
            #self.widget.labelCode.setText('식별 코드 : ' + name)
            #self.widget.labelCode.repaint()
            #time.sleep(0.5)
            pre_name = name

            # 한번 인식하면 잠깐 인식 멈추기
            self.widget.isNeedDetection = False

            # 소켓 서버에 인증 결과 전송
            hashcode = hashlib.sha256(str(data).encode()).hexdigest()
            personInfo = {'name': name, 'hashcode': hashcode}
            self.isProcessingPay = True
            sio.emit('identifyForPay', personInfo)

            while self.isProcessingPay:
                sio.on('identifyForPay', self.finish)

            #time.sleep(0.5)
            pre_name = name

    def finish(self, result):
        self.isProcessingPay = False
        if result == 'completed':
            print('인증 및 검증 성공')
            self.widget.labelCode.setText('식별 코드 : ' + name)
            self.widget.labelCode.repaint()
        else:
            print('데이터 위변조 탐지')
            self.widget.labelCode.setText('식별 코드 : 위변조 탐지')
            self.widget.labelCode.repaint()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    sys.exit(app.exec_())