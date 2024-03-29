# ----------------------------------------------------------
# breakout.py  Game I2C display version
#  ESP8266 (node MCU D1 mini)  micropython
# by Billy Cheung  2019 08 31
#

#
# I2C OLED SSD1306
# GPIO4   D2---  SDA OLED
# GPIO5   D1---  SCL  OLED
#
# Speaker
# GPIO15  D8     Speaker
#
#buttons
# GPIO12  D6——  Left  
# GPIO13  D7——  Right     
# GPIO14  D5——  UP    
# GPIO2   D4——   Down    
# GPIO0   D3——   A
import gc
import sys
gc.collect()
print (gc.mem_free())
import network
import utime
from utime import sleep_ms,ticks_ms, ticks_us, ticks_diff
from machine import Pin, I2C,PWM, ADC
from math import sqrt
import ssd1306
from random import getrandbits, seed

#--------- pin layout
SCREEN_WIDTH  = const(128)
SCREEN_HEIGHT = const(64)
paddle_width = 22
btnLeft = Pin(12, Pin.IN, Pin.PULL_UP)
btnRight = Pin(13, Pin.IN, Pin.PULL_UP)
btnUp = Pin(14, Pin.IN, Pin.PULL_UP)
btnDown = Pin(2, Pin.IN, Pin.PULL_UP)
btnA = Pin(0, Pin.IN, Pin.PULL_UP)
buzzer = Pin(15, Pin.OUT)
# configure oled display I2C SSD1306
i2c = I2C(-1, Pin(5), Pin(4))   # SCL, SDA
display = ssd1306.SSD1306_I2C(128, 64, i2c)
# ESP8266 ADC A0 values 0-1023
adc = ADC(0)


def pressed (btn, wait_release=False) :
  if not btn.value():
    if btn.value():
      return False
    #wait for key release
    while wait_release and not btn.value() :
      sleep_ms (5)
    return True
  return False

tones = {
    'c4': 262,
    'd4': 294,
    'e4': 330,
    'f4': 349,
    'f#4': 370,
    'g4': 392,
    'g#4': 415,
    'a4': 440,
    "a#4": 466,
    'b4': 494,
    'c5': 523,
    'c#5': 554,
    'd5': 587,
    'd#5': 622,
    'e5': 659,
    'f5': 698,
    'f#5': 740,
    'g5': 784,
    'g#5': 831,
    'a5': 880,
    'b5': 988,
    'c6': 1047,
    'c#6': 1109,
    'd6': 1175,
    ' ': 0
}


def playTone(tone, tone_duration, rest_duration=0):
  beeper = PWM(buzzer, freq=tones[tone], duty=512)
  utime.sleep_ms(tone_duration)
  beeper.deinit()
  utime.sleep_ms(rest_duration)

def playSound(freq, tone_duration, rest_duration=0):
  beeper = PWM(buzzer, freq, duty=512)
  utime.sleep_ms(tone_duration)
  beeper.deinit()
  utime.sleep_ms(rest_duration)




class Ball(object):
    """Ball."""

    def __init__(self, x, y, x_speed, y_speed, display, width=2, height=2,
                 frozen=False):
        self.x = x
        self.y = y
        self.x2 = x + width - 1
        self.y2 = y + height - 1
        self.prev_x = x
        self.prev_y = y
        self.width = width
        self.height = height
        self.center = width // 2
        self.max_x_speed = 3
        self.max_y_speed = 3
        self.frozen = frozen
        self.display = display
        self.x_speed = x_speed
        self.y_speed = y_speed
        self.x_speed2 = 0.0
        self.y_speed2 = 0.0
        self.created = ticks_ms()

    def clear(self):
        """Clear ball."""
        self.display.fill_rect(self.x, self.y, self.width, self.height, 0)

    def clear_previous(self):
        """Clear prevous ball position."""
        self.display.fill_rect(self.prev_x, self.prev_y,
                                self.width, self.height, 0)

    def draw(self):
        """Draw ball."""
        self.clear_previous()
        self.display.fill_rect( self.x, self.y,
                                 self.width, self.height,1)

    def set_position(self, paddle_x, paddle_y, paddle_x2, paddle_center):
        bounced = False
        """Set ball position."""
        self.prev_x = self.x
        self.prev_y = self.y
        # Check if frozen to paddle
        if self.frozen:
            # Freeze ball to top center of paddle
            self.x = paddle_x + (paddle_center - self.center)
            self.y = paddle_y - self.height
            if ticks_diff(ticks_ms(), self.created) >= 2000:
                # Release frozen ball after 2 seconds
                self.frozen = False
            else:
                return
        self.x += int(self.x_speed) + int(self.x_speed2)
        self.x_speed2 -= int(self.x_speed2)
        self.x_speed2 += self.x_speed - int(self.x_speed)

        self.y += int(self.y_speed) + int(self.y_speed2)
        self.y_speed2 -= int(self.y_speed2)
        self.y_speed2 += self.y_speed - int(self.y_speed)

        # Bounces off walls
        if self.y < 10:
            self.y = 10
            self.y_speed = -self.y_speed
            bounced = True
        if self.x + self.width >= 125:
            self.x = 125 - self.width
            self.x_speed = -self.x_speed
            bounced = True
        elif self.x < 3:
            self.x = 3
            self.x_speed = -self.x_speed
            bounced = True

        # Check for collision with Paddle
        if (self.y2 >= paddle_y and
           self.x <= paddle_x2 and
           self.x2 >= paddle_x):
            # Ball bounces off paddle
            self.y = paddle_y - (self.height + 1)
            ratio = ((self.x + self.center) -
                     (paddle_x + paddle_center)) / paddle_center
            self.x_speed = ratio * self.max_x_speed
            self.y_speed = -sqrt(max(1, self.max_y_speed ** 2 - self.x_speed ** 2))
            bounced = True

        self.x2 = self.x + self.width - 1
        self.y2 = self.y + self.height - 1
        return bounced


class Brick(object):
    """Brick."""

    def __init__(self, x, y, color, display, width=12, height=2):
        """Initialize brick.

        Args:
            x, y (int):  X,Y coordinates.
            color (string):  Blue, Green, Pink, Red or Yellow.
            display (SSD1351): OLED display.
            width (Optional int): Blick width
            height (Optional int): Blick height
        """
        self.x = x
        self.y = y
        self.x2 = x + width - 1
        self.y2 = y + height - 1
        self.center_x = x + (width // 2)
        self.center_y = y + (height // 2)
        self.color = color
        self.width = width
        self.height = height
        self.display = display
        self.draw()

    def bounce(self, ball_x, ball_y, ball_x2, ball_y2,
               x_speed, y_speed,
               ball_center_x, ball_center_y):
        """Determine bounce for ball collision with brick."""
        x = self.x
        y = self.y
        x2 = self.x2
        y2 = self.y2
        center_x = self.center_x
        center_y = self.center_y
        if ((ball_center_x > center_x) and
           (ball_center_y > center_y)):
            if (ball_center_x - x2) < (ball_center_y - y2):
                y_speed = -y_speed
            elif (ball_center_x - x2) > (ball_center_y - y2):
                x_speed = -x_speed
            else:
                x_speed = -x_speed
                y_speed = -y_speed
        elif ((ball_center_x > center_x) and
              (ball_center_y < center_y)):
            if (ball_center_x - x2) < -(ball_center_y - y):
                y_speed = -y_speed
            elif (ball_center_x - x2) > -(ball_center_y - y):
                x_speed = -x_speed
            else:
                x_speed = -x_speed
                y_speed = -y_speed
        elif ((ball_center_x < center_x) and
              (ball_center_y < center_y)):
            if -(ball_center_x - x) < -(ball_center_y - y):
                y_speed = -y_speed
            elif -(ball_center_x - x) > -(ball_center_y - y):
                y_speed = -y_speed
            else:
                x_speed = -x_speed
                y_speed = -y_speed
        elif ((ball_center_x < center_x) and
              (ball_center_y > center_y)):
            if -(ball_center_x - x) < (ball_center_y - y2):
                y_speed = -y_speed
            elif -(ball_center_x - x) > (ball_center_y - y2):
                x_speed = -x_speed
            else:
                x_speed = -x_speed
                y_speed = -y_speed

        return [x_speed, y_speed]

    def clear(self):
        """Clear brick."""
        self.display.fill_rect(self.x, self.y, self.width, self.height, 0)

    def draw(self):
        """Draw brick."""
        self.display.fill_rect(self.x, self.y, self.width, self.height, 1)


class Life(object):
    """Life."""

    def __init__(self, index, display, width=4, height=6):
        """Initialize life.

        Args:
            index (int): Life number (1-based).
            display (SSD1351): OLED display.
            width (Optional int): Life width
            height (Optional int): Life height
        """
        margin = 5
        self.display = display
        self.x = display.width - (index * (width + margin))
        self.y = 0
        self.width = width
        self.height = height
        self.draw()

    def clear(self):
        """Clear life."""
        self.display.fill_rect(self.x, self.y, self.width, self.height, 0)

    def draw(self):
        """Draw life."""
        self.display.fill_rect(self.x, self.y,
                                 self.width, self.height,1)


class Paddle(object):
    """Paddle."""

    def __init__(self, display, width, height):
        """Initialize paddle.

        Args:
            display (SSD1306): OLED display.
            width (Optional int): Paddle width
            height (Optional int): Paddle height
        """
        self.x = 55
        self.y = 60
        self.x2 = self.x + width - 1
        self.y2 = self.y + height - 1
        self.width = width
        self.height = height
        self.center = width // 2
        self.display = display

    def clear(self):
        """Clear paddle."""
        self.display.fill_rect(self.x, self.y, self.width, self.height, 0)

    def draw(self):
        """Draw paddle."""
        self.display.fill_rect(self.x, self.y,
                                 self.width, self.height,1)

    def h_position(self, x):
        """Set paddle position.

        Args:
            x (int):  X coordinate.
        """
        new_x = max(3,min (x, 125-self.width))
        if new_x != self.x :  # Check if paddle moved
            prev_x = self.x  # Store previous x position
            self.x = new_x
            self.x2 = self.x + self.width - 1
            self.y2 = self.y + self.height - 1
            self.draw()
            # Clear previous paddle
            if x > prev_x:
                self.display.fill_rect(prev_x, self.y,
                                        x - prev_x, self.height, 0)
            else:
                self.display.fill_rect(x + self.width, self.y,
                                        (prev_x + self.width) -
                                        (x + self.width),
                                        self.height, 0)
        else:
            self.draw()

class Score(object):
    """Score."""

    def __init__(self, display):
        """Initialize score.

        Args:
            display (SSD1306): OLED display.
        """
        margin = 5
        self.display = display
        self.display.text('SCORE:', margin, 0, 1)
        self.x = 50 + margin
        self.y = 0
        self.value = 0
        self.draw()

    def draw(self):
        """Draw score value."""
        self.display.fill_rect(self.x, self.y, 20, 8, 0)
        self.display.text( str(self.value), self.x, self.y,1)

    def game_over(self):
        """Display game_over."""
        self.display.text('GAME OVER', (self.display.width // 2) - 30,
                               int(self.display.height / 1.5), 1)

    def increment(self, points):
        """Increase score by specified points."""
        self.value += points
        self.draw()

def load_level(level, display) :

    bricks = []
    for row in range(12, 20 + 6 * level , 6):
        brick_color = 1
        for col in range(8, 112, 15 ):
            bricks.append(Brick(col, row, brick_color, display))
    return bricks





# Seed random numbers
seed(ticks_us())
exitGame = False
while not exitGame :

    gc.collect()
    print (gc.mem_free())

    display.fill(0)
    display.text('BREAKOUT', 5, 0, 1)
    display.text('U = Button', 5, 20, 1)
    display.text('D = Paddle', 5, 35,  1)
    display.text('L = Exit', 5, 50,  1)
    display.show()
    gameover = False
    wait_for_keys= True
    usePaddle = False
    while wait_for_keys:
      if pressed(btnUp) :
        wait_for_keys=False
      elif pressed(btnDown) :
        usePaddle = True
        wait_for_keys=False
      elif pressed(btnLeft,True) :
        wait_for_keys=False
        exitGame = True
        game_over = True

    if not exitGame :
      display.fill(0)

      # Generate bricks
      MAX_LEVEL = const(5)
      level = 1
      bricks = load_level(level, display)

      # Initialize paddle
      paddle = Paddle(display, paddle_width, 3)

      # Initialize score
      score = Score(display)

      # Initialize balls
      balls = []
      # Add first ball
      balls.append(Ball(59, 58, -2, -1, display, frozen=True))

      # Initialize lives
      lives = []
      for i in range(1, 3):
          lives.append(Life(i, display))
      print (len(lives))

      prev_paddle_vect = 0


      display.show()


      try:
          while not gameover :
              timer = ticks_ms()
              if usePaddle :
                  # Set paddle position to ADC spinner (scale 1 - 107)
                  paddle.h_position(int(adc.read() // 9.57))
              else :
                  paddle_vect = 0
                  if not btnLeft.value():
                    paddle_vect = -1
                  if not btnRight.value():
                    paddle_vect = 1
                  if paddle_vect != prev_paddle_vect :
                    paddle_vect *= 3
                  else :
                    paddle_vect *= 5
                  paddle.h_position(paddle.x + paddle_vect)
                  prev_paddle_vect = paddle_vect

               # Handle balls
              score_points = 0
              for ball in balls:
                  # move ball and check if bounced off walls and paddle
                  if ball.set_position(paddle.x, paddle.y,paddle.x2, paddle.center):
                      playSound(2000, 10)
                  # Check for collision with bricks if not frozen
                  if not ball.frozen:
                      prior_collision = False
                      ball_x = ball.x
                      ball_y = ball.y
                      ball_x2 = ball.x2
                      ball_y2 = ball.y2
                      ball_center_x = ball.x + ((ball.x2 + 1 - ball.x) // 2)
                      ball_center_y = ball.y + ((ball.y2 + 1 - ball.y) // 2)

                      # Check for hits
                      for brick in bricks:
                          if(ball_x2 >= brick.x and
                             ball_x <= brick.x2 and
                             ball_y2 >= brick.y and
                             ball_y <= brick.y2):
                              # Hit
                              if not prior_collision:
                                  ball.x_speed, ball.y_speed = brick.bounce(
                                      ball.x,
                                      ball.y,
                                      ball.x2,
                                      ball.y2,
                                      ball.x_speed,
                                      ball.y_speed,
                                      ball_center_x,
                                      ball_center_y)
                                  playTone('c6', 10)
                                  prior_collision = True
                              score_points += 1
                              brick.clear()
                              bricks.remove(brick)

                  # Check for missed
                  if ball.y2 > display.height - 2:
                      ball.clear_previous()
                      balls.remove(ball)
                      if not balls:
                          # Lose life if last ball on screen
                          if len(lives) == 0:
                              score.game_over()
                              playTone('g4', 500)
                              playTone('c5', 300)
                              playTone('f4', 500)
                              gameover = True
                          else:
                              # Subtract Life
                              lives.pop().clear()
                              # Add ball
                              balls.append(Ball(59, 58, 2, -3, display,
                                           frozen=True))
                  else:
                      # Draw ball
                      ball.draw()
              # Update score if changed
              if score_points:
                  score.increment(score_points)

              # Check for level completion
              if not bricks:
                  for ball in balls:
                      ball.clear()
                  balls.clear()
                  level += 1
                  paddle_width -=2
                  if level > MAX_LEVEL:
                      level = 1
                  bricks = load_level(level, display)
                  balls.append(Ball(59, 58, -2, -1, display, frozen=True))
                  playTone('c5', 20)
                  playTone('d5', 20)
                  playTone('e5', 20)
                  playTone('f5', 20)
                  playTone('g5', 20)
                  playTone('a5', 20)
                  playTone('b5', 20)
                  playTone('c6', 20)
              display.show()
              # Attempt to set framerate to 50 FPS
              timer_dif = int(1000 / 60) - ticks_diff(ticks_ms(), timer)
              if timer_dif > 0:
                  sleep_ms(timer_dif)
      except KeyboardInterrupt:
          display.cleanup()

      sleep_ms(2000)
