#include <TimerOne.h>

#include <math.h>
#include <stdint.h>

#define sign(x) ((x > 0) - (x < 0))
#define MAX(x, y) ((x) < (y) ? (y) : (x))

// #define DEBUG

#define ROTARY_EN 4
#define ROTARY_STEP 5
#define ROTARY_DIR 6
#define ROTARY_LIMIT A0
#define LINEAR_EN 7
#define LINEAR_STEP 8
#define LINEAR_DIR 9
#define LINEAR_LIMIT A1

#define STEPS_PER_CIRCLE 25600
#define RADS_TO_STEPS STEPS_PER_CIRCLE / (2.0 * M_PI)

// All values in steps
int cur_theta, cur_r, cur_x, cur_y;
int debug_counter = 0;

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
  pinMode(ROTARY_LIMIT, INPUT);
  pinMode(LINEAR_EN, OUTPUT);
  digitalWrite(LINEAR_EN, HIGH);
  pinMode(LINEAR_STEP, OUTPUT);
  pinMode(LINEAR_DIR, OUTPUT);
  pinMode(LINEAR_LIMIT, INPUT);
  digitalWrite(LINEAR_LIMIT, HIGH);
  
  pinMode(13, OUTPUT);

  Serial.begin(38400);
  
  Timer1.initialize(100000);
  
  cur_theta = 0;
  cur_r = 0;
  cur_x = 0;
  cur_y = 0;
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

void enable_steppers(int interval) {
  digitalWrite(ROTARY_EN, LOW);
  digitalWrite(LINEAR_EN, LOW);
  digitalWrite(13, HIGH);
  phase = PHASE_UP_EDGE;
  Timer1.attachInterrupt(timer_func, interval >> 1);
}

void disable_steppers() {
  Timer1.detachInterrupt();
  delayMicroseconds(1);
  digitalWrite(ROTARY_EN, HIGH);
  digitalWrite(LINEAR_EN, HIGH);
  digitalWrite(13, LOW);
}

void do_step(int target_r, int target_theta) {
  // Radius step
  if(target_r != cur_r) {
    digitalWrite(LINEAR_DIR, target_r > cur_r);
    digitalWrite(LINEAR_STEP, HIGH);
    cur_r += sign(target_r - cur_r);
  }

  // Rotary step
  if(target_theta != cur_theta) {
    if(abs(target_theta - cur_theta) < STEPS_PER_CIRCLE / 2) {
      digitalWrite(ROTARY_DIR, target_theta > cur_theta);
      cur_theta += sign(target_theta - cur_theta);
    } else {
      digitalWrite(ROTARY_DIR, target_theta < cur_theta);
      cur_theta = (cur_theta + sign(cur_theta - target_theta));
      if(cur_theta < 0)
        cur_theta += STEPS_PER_CIRCLE;
      else if(cur_theta > STEPS_PER_CIRCLE)
        cur_theta -= STEPS_PER_CIRCLE;
    }
    digitalWrite(ROTARY_STEP, HIGH);
  }
}

void do_move_xy(int x, int y, int interval) {
  long dx = x - cur_x;
  long dy = y - cur_y;
  float distance = sqrt(dx*dx + dy*dy);
  int steps = (int)distance;
  float stepx = dx / distance;
  float stepy = dy / distance;

#ifdef DEBUG
  Serial.print("LOG dx = ");
  Serial.print(dx);
  Serial.print(", dy = ");
  Serial.print(dy);
  Serial.print(", distance = ");
  Serial.println(distance);
#endif

  enable_steppers(interval);
  
  // Interpolation counter
  int i = 0;
  // Values in steps
  float fcur_x = cur_x, fcur_y = cur_y;
  int target_theta = cur_theta, target_r = cur_r;
  while(i <= distance) {
    if(target_theta == cur_theta && target_r == cur_r) {
      i += 1;
      fcur_x += stepx;
      fcur_y += stepy;
      target_r = sqrt(fcur_x * fcur_x + fcur_y * fcur_y);
      target_theta = (atan2(fcur_y, fcur_x) + M_PI) * RADS_TO_STEPS;
    }

    while(phase != PHASE_UP_EDGE);

#ifdef DEBUG
    if(debug_counter == 0) {
      Serial.print("LOG target_r = ");
      Serial.print(target_r);
      Serial.print(", cur_r = ");
      Serial.print(cur_r);
      Serial.print(", target_theta = ");
      Serial.print(target_theta);
      Serial.print(", cur_theta = ");
      Serial.print(cur_theta);
      Serial.print(", cur_x = ");
      Serial.print((int)fcur_x);
      Serial.print(", cur_y = ");
      Serial.println((int)fcur_y);
    }
    debug_counter = (debug_counter + 1) % 250;
#endif

    do_step(target_r, target_theta);
    phase = PHASE_IDLE;
  }

  disable_steppers();
  cur_x = fcur_x;
  cur_y = fcur_y;

#ifdef DEBUG
  Serial.print("LOG Final x = ");
  Serial.print(cur_x);
  Serial.print(", y =");
  Serial.println(cur_y);
#endif
}

void do_move_polar(int dr, int dtheta, int interval) {
  int distance = abs(MAX(dr, dtheta));
  float deltar = float(dr) / distance;
  float deltatheta = float(dtheta) / distance;
  float t = 0.0;

#ifdef DEBUG
  Serial.print("LOG dr = ");
  Serial.print(dr);
  Serial.print(", dtheta = ");
  Serial.print(dtheta);
  Serial.print(", distance = ");
  Serial.print(distance);
  Serial.print(", deltar = ");
  Serial.print(deltar);
  Serial.print(", deltatheta = ");
  Serial.println(deltatheta);
#endif
  
  // Used to keep sub-step accuracy in interpolation
  float target_r = cur_r, target_theta = cur_theta;
  float stepsize;
  
  enable_steppers(interval);

  while(t < distance) {
    if(cur_r == (int)target_r && cur_theta == (int)target_theta) {
      if(cur_r != 0) {
        stepsize = STEPS_PER_CIRCLE / (2 * M_PI * cur_r);
      } else {
        stepsize = 1 / deltar;
      }
      t += stepsize;
      target_r += deltar * stepsize;
      target_theta += deltatheta * stepsize;
    }
    
    while(phase != PHASE_UP_EDGE);
    
#ifdef DEBUG
    if(debug_counter == 0) {
      Serial.print("LOG target_r = ");
      Serial.print(target_r);
      Serial.print(", cur_r = ");
      Serial.print(cur_r);
      Serial.print(", target_theta = ");
      Serial.print(target_theta);
      Serial.print(", cur_theta = ");
      Serial.print(cur_theta);
      Serial.print(", t = ");
      Serial.println(t);
    }
    debug_counter = (debug_counter + 1) % 250;
#endif

    do_step((int)target_r, (int)target_theta);
    phase = PHASE_IDLE;
  }
  
  disable_steppers();
  cur_x = sin(cur_theta / RADS_TO_STEPS) * cur_r;
  cur_y = cos(cur_theta / RADS_TO_STEPS) * cur_r;

#ifdef DEBUG
  Serial.print("LOG Final r = ");
  Serial.print(cur_r);
  Serial.print(", theta = ");
  Serial.println(cur_theta);
#endif
}

void do_zero(int interval) {
  int linear_limit = LOW;
  int rotary_limit = LOW;
  
  enable_steppers(interval);
  digitalWrite(LINEAR_DIR, LOW);
  digitalWrite(ROTARY_DIR, HIGH);
  
  while(!(linear_limit && rotary_limit)) {
    while(phase != PHASE_UP_EDGE);

    if(!linear_limit) {
      linear_limit = !digitalRead(LINEAR_LIMIT);
      digitalWrite(LINEAR_STEP, HIGH);
    }
    if(!rotary_limit) {
      rotary_limit = !digitalRead(ROTARY_LIMIT);
      digitalWrite(ROTARY_STEP, HIGH);
    }

    phase = PHASE_IDLE;
    
#ifdef DEBUG
    if(debug_counter == 0) {
      Serial.print("LOG linear_limit = ");
      Serial.print(LINEAR_LIMIT);
      Serial.print(", rotary_limit = ");
      Serial.println(rotary_limit);
    }
    debug_counter = (debug_counter + 1) % 250;
#endif
  }
  
  disable_steppers();
  cur_x = cur_y = cur_r = cur_theta = 0;
}

void move_xy() {
  char buf[64];
  int x, y;
  read_line(buf);
  sscanf(buf, "%ld %ld", &x, &y);
  Serial.println("OK");
  do_move_xy(x, y, interval);
}

void move_polar() {
  char buf[64];
  int r, theta;
  read_line(buf);
  sscanf(buf, "%ld %ld", &r, &theta);
  Serial.println("OK");
  do_move_polar(r, theta, interval);
}

void speed() {
  char buf[8];
  read_line(buf);
  sscanf(buf, "%d", &interval);
  Serial.println("OK");
}

void zero() {
  char buf[64];
  read_line(buf);
  Serial.println("OK");
  do_zero(interval);
}

void noop() {
  char buf[64];
  read_line(buf);
  Serial.println("OK");
}

struct command_t {
  char name;
  void (*func)();
} commands[] = {
  {'m', move_xy},
  {'p', move_polar},
  {'s', speed},
  {'0', zero},
  {'n', noop},
  {'\0', NULL}
};

void loop() {
  char cmd;
  for(;;) {
    while(!Serial.available());
    cmd = (char)Serial.read();
    for(struct command_t *def = commands; def->func != NULL; def++) {
      if(def->name == cmd) {
        Serial.read(); // Discard space
        def->func();
        break;
      }
    }
  }
}

