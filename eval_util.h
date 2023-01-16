#ifndef EVAL_UTIL_H
#define EVAL_UTIL_H

#include <stdlib.h>
#include <limits.h>

#define EVAL_UTIL_H_SEED 172812

void
eval_rand_fill_buf(unsigned char* buf, int buf_len)
{
  for (int ii = 0; ii < buf_len; ++ii) {
    buf[ii] = rand() % UCHAR_MAX;
  }
}

#endif // EVAL_UTIL_H
