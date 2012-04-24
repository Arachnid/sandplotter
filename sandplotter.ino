#include <TimerOne.h>

#include <math.h>
#include <stdint.h>

#define sign(x) ((x > 0) - (x < 0))

#define ROTARY_EN 4
#define ROTARY_STEP 5
#define ROTARY_DIR 6
#define LINEAR_EN 7
#define LINEAR_STEP 8
#define LINEAR_DIR 9

#define STEPS_PER_CIRCLE 25600
#define RADS_TO_STEPS STEPS_PER_CIRCLE / (2.0 * M_PI)

// All values in steps
int cur_theta;
int cur_r;

float cur_x, cur_y;

int interval = 1000;

void read_line(char *buf) {
  char *bufptr = buf;
  for(;;) {
    if(Serial.available() > 0) {
      *bufptr = (char)Serial.read();
      if(*bufptr == '\r' || *bufptr == '\n') {
        *bufptr = '\0';
        return;
      } else {
        bufptr++;
      }
    }
  }
}

void discard_line() {
  // Ignore everything until newline
  for(;;) {
    if(Serial.available() > 0) {
      char in = (char)Serial.read();
      if(in == '\r' || in == '\n')
        break;
    }
  }
}

void setup() {
  // Configure pins
  pinMode(ROTARY_EN, OUTPUT);
  digitalWrite(ROTARY_EN, HIGH);
  pinMode(ROTARY_STEP, OUTPUT);
  pinMode(ROTARY_DIR, OUTPUT);
  pinMode(LINEAR_EN, OUTPUT);
  digitalWrite(LINEAR_EN, HIGH);
  pinMode(LINEAR_STEP, OUTPUT);
  pinMode(LINEAR_DIR, OUTPUT);

  Serial.begin(38400);
  
  Timer1.initialize(100000);
  
  cur_theta = 0;
  cur_r = 0;
  cur_x = cur_y = 0.0;
}

// PHASE_UP_EDGE: Move function runs, sets state to PHASE_IDLE
// PHASE_IDLE: ISR clears step pins, sets state to PHASE_DOWN_EDGE
// PHASE_DOWN_EDGE: ISR sets state to PHASE_UP_EDGE

#define PHASE_UP_EDGE 0 
#define PHASE_IDLE 1
#define PHASE_DOWN_EDGE 2

volatile int phase;

void timer_func() {
  if(phase == PHASE_IDLE) {
    // Reset the step pins
    digitalWrite(ROTARY_STEP, LOW);
    digitalWrite(LINEAR_STEP, LOW);
    phase = PHASE_DOWN_EDGE;
  } else if(phase == PHASE_DOWN_EDGE) {
    phase = PHASE_UP_EDGE;
  }
}

int do_step(int step_pin, int dir_pin, int increment) {
  if(increment != 0) {
    digitalWrite(dir_pin, increment == 1);
    digitalWrite(step_pin, HIGH);
  }
  return increment;
}

void do_move(int x, int y, int interval) {
  long dx = x - cur_x;
  long dy = y - cur_y;
  float distance = sqrt(dx*dx + dy*dy);
  int steps = (int)distance;
  float stepx = dx / distance;
  float stepy = dy / distance;
  
  digitalWrite(ROTARY_EN, LOW);
  digitalWrite(LINEAR_EN, LOW);
  phase = PHASE_UP_EDGE;
  Timer1.attachInterrupt(timer_func, interval >> 1);
  
  // Interpolation counter
  int i = 0;
  // Values in steps
  int target_theta = cur_theta, target_r = cur_r;
  while(i <= distance) {
    if(target_theta == cur_theta && target_r == cur_r) {
      i += 1;
      cur_x += stepx;
      cur_y += stepy;
      target_r = sqrt(cur_x * cur_x + cur_y * cur_y);
      target_theta = atan2(cur_y, cur_x) * RADS_TO_STEPS;
    }
    while(phase != PHASE_UP_EDGE);
    cur_r += do_step(LINEAR_STEP, LINEAR_DIR, sign(target_r - cur_r));
    if(abs(target_theta - cur_theta) < STEPS_PER_CIRCLE / 2) {
      cur_theta += do_step(ROTARY_STEP, ROTARY_DIR, sign(target_theta - cur_theta));
    } else {
      cur_theta = (cur_theta + do_step(ROTARY_STEP, ROTARY_DIR, sign(cur_theta - target_theta))) % STEPS_PER_CIRCLE;
      if(cur_theta < 0)
        cur_theta += STEPS_PER_CIRCLE;
    }
    phase = PHASE_IDLE;
  }

  Timer1.detachInterrupt();
  delayMicroseconds(1);
  digitalWrite(ROTARY_EN, HIGH);
  digitalWrite(LINEAR_EN, HIGH);
}

void move() {
  char buf[64];
  int x, y;
  read_line(buf);
  sscanf(buf, " %ld %ld", &x, &y);
  Serial.println("OK");
  do_move(x, y, interval);
}

void speed() {
  char buf[8];
  read_line(buf);
  sscanf(buf, " %d", &interval);
  Serial.println("OK");
}

struct command_t {
  char name;
  void (*func)();
} commands[] = {
  {'m', move},
  {'s', speed},
  {'\0', NULL}
};

void loop() {
  char cmd;
  for(;;) {
    while(!Serial.available());
    cmd = (char)Serial.read();
    for(struct command_t *def = commands; def->func != NULL; def++) {
      if(def->name == cmd) {
        def->func();
        break;
      }
    }
  }
}

